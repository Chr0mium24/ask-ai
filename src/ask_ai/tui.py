from __future__ import annotations

from collections.abc import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Input,
    Label,
    ListView,
    SelectionList,
)

from ask_ai.client import (
    CompletionResult,
    DEFAULT_BASE_URL,
    DEFAULT_SYSTEM_PROMPT,
    MODEL_LABELS,
    DeepSeekClient,
    DeepSeekError,
    ModelKey,
)
from ask_ai.sessions import SessionStore
from ask_ai.tui_actions import AskActionsMixin
from ask_ai.tui_styles import APP_CSS
from ask_ai.tui_widgets import MessageBubble, SessionItem


class AskApp(AskActionsMixin, App[None]):
    CSS = APP_CSS

    BINDINGS = [
        Binding("tab", "toggle_mode", "Toggle mode", show=False, priority=True),
        Binding("ctrl+c", "clear_prompt", "Clear prompt", show=False, priority=True),
        Binding("ctrl+z", "restore_prompt", "Restore prompt", show=False, priority=True),
    ]

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        store_factory: Callable[[], SessionStore] = SessionStore,
    ) -> None:
        super().__init__()
        self.client = DeepSeekClient(base_url=base_url)
        self.system_prompt = system_prompt
        self.store = store_factory()
        self.session = self.store.load_or_create_latest()
        self.model: ModelKey = "flash"
        self.pending = False
        self.manage_mode = False
        self.sidebar_width = 20
        self.last_cleared_prompt = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                with Horizontal(id="session-actions"):
                    yield Button("New", id="new-session")
                    yield Button("Del", variant="error", id="delete-session")
                yield ListView(id="sessions")
            with Vertical(id="main"):
                yield VerticalScroll(id="transcript")
                yield SelectionList[str](id="manage-list")
                yield Label("", id="token-usage")
                yield Input(placeholder="Message or /model /clear /quit", id="prompt")

    async def on_mount(self) -> None:
        await self._render_sessions()
        await self._render_active_view()
        self.query_one("#prompt", Input).focus()

    async def action_toggle_mode(self) -> None:
        self.manage_mode = not self.manage_mode
        await self._render_active_view()

    def action_clear_prompt(self) -> None:
        if self.screen.id != "_default":
            return

        prompt = self.query_one("#prompt", Input)
        if not prompt.value:
            return

        self.last_cleared_prompt = prompt.value
        prompt.value = ""
        prompt.focus()

    def action_restore_prompt(self) -> None:
        if self.screen.id != "_default" or not self.last_cleared_prompt:
            return

        prompt = self.query_one("#prompt", Input)
        if prompt.value:
            return

        prompt.value = self.last_cleared_prompt
        prompt.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "new-session":
            await self._new_session()
            return
        if button_id == "delete-session":
            self._confirm_delete_session(self.session.id)
            return

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        session_id = getattr(item, "session_id", None)
        if not isinstance(session_id, str) or session_id == self.session.id:
            return

        loaded = self.store.load(session_id)
        if loaded is None:
            return

        self.session = loaded
        self.manage_mode = False
        await self._render_sessions()
        await self._render_active_view()
        self.query_one("#prompt", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt or self.pending:
            return

        input_widget = self.query_one("#prompt", Input)
        input_widget.value = ""

        if prompt.startswith("/"):
            await self._handle_command(prompt)
            return

        await self._send_prompt(prompt)

    async def on_selection_list_selected_changed(
        self,
        event: SelectionList.SelectedChanged,
    ) -> None:
        if event.selection_list.id != "manage-list":
            return

        selected = set(event.selection_list.selected)
        for summary in self.session.turn_summaries():
            self.session.set_turn_included(summary.turn_id, summary.turn_id in selected)
        self.store.save(self.session)

    async def _handle_command(self, command: str) -> None:
        parts = command.split()
        name = parts[0]

        if name == "/clear":
            self.session.clear()
            self.store.save(self.session)
            self.manage_mode = False
            await self._render_sessions()
            await self._render_active_view()
            return

        if name == "/quit":
            self.exit()
            return

        if name == "/new":
            await self._new_session()
            return

        if name == "/model":
            await self._set_model(parts[1:])
            return

        if name == "/sidebar":
            await self._set_sidebar_width(parts[1:])
            return

        if name == "/delete-session":
            self._confirm_delete_session(self.session.id)
            return

        await self._append_status(f"unknown command: {command}")

    async def _set_model(self, args: list[str]) -> None:
        if not args:
            self.model = "pro" if self.model == "flash" else "flash"
        elif len(args) == 1 and args[0] in MODEL_LABELS:
            self.model = args[0]  # type: ignore[assignment]
        else:
            await self._append_status("usage: /model [flash|pro]")
            return

        await self._append_status(f"model: {MODEL_LABELS[self.model]}")
        self._render_token_usage()

    async def _set_sidebar_width(self, args: list[str]) -> None:
        if len(args) != 1:
            await self._append_status(f"sidebar width: {self.sidebar_width}")
            return

        try:
            width = int(args[0])
        except ValueError:
            await self._append_status("usage: /sidebar 12-40")
            return

        self.sidebar_width = max(12, min(40, width))
        self.query_one("#sidebar", Vertical).styles.width = self.sidebar_width
        await self._append_status(f"sidebar width: {self.sidebar_width}")

    async def _send_prompt(self, prompt: str) -> None:
        input_widget = self.query_one("#prompt", Input)
        input_widget.disabled = True
        self.pending = True
        request_model = self.model

        turn_id = self.session.add_user_message(prompt)
        self.store.save(self.session)
        await self._render_sessions()
        await self._render_chat()
        status = await self._append_status(f"asking {MODEL_LABELS[request_model]}...")

        try:
            result = await self._complete_with_usage(
                self.session.context_messages(limit=30),
                model=request_model,
                system_prompt=self.system_prompt,
            )
            self.session.add_assistant_message(
                result.content,
                turn_id=turn_id,
                model=request_model,
                token_usage=result.usage,
            )
            self.store.save(self.session)
            await status.remove()
            await self._render_sessions()
            await self._render_chat()
        except DeepSeekError as exc:
            status.update(f"error: {exc}")
        finally:
            input_widget.disabled = False
            input_widget.focus()
            self.pending = False

    async def _complete_with_usage(
        self,
        messages: list[dict[str, str]],
        *,
        model: ModelKey,
        system_prompt: str,
    ) -> CompletionResult:
        complete_with_usage = getattr(self.client, "complete_with_usage", None)
        if complete_with_usage is not None:
            return await complete_with_usage(
                messages,
                model=model,
                system_prompt=system_prompt,
            )

        content = await self.client.complete(
            messages,
            model=model,
            system_prompt=system_prompt,
        )
        return CompletionResult(content=content)

    async def _new_session(self) -> None:
        self.session = self.store.create()
        self.manage_mode = False
        await self._render_sessions()
        await self._render_active_view()
        self.query_one("#prompt", Input).focus()

    async def _render_sessions(self) -> None:
        sessions = self.store.list_sessions()
        session_list = self.query_one("#sessions", ListView)
        await session_list.clear()
        await session_list.extend(SessionItem(session) for session in sessions)
        for index, item in enumerate(session_list.children):
            if getattr(item, "session_id", None) == self.session.id:
                session_list.index = index
                break

    async def _render_active_view(self) -> None:
        transcript = self.query_one("#transcript", VerticalScroll)
        manage_list = self.query_one("#manage-list", SelectionList)
        transcript.display = not self.manage_mode
        manage_list.display = self.manage_mode
        if self.manage_mode:
            await self._render_manage()
        else:
            await self._render_chat()
        self._render_token_usage()

    async def _render_chat(self) -> None:
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.remove_children()
        for message in self.session.messages:
            await transcript.mount(MessageBubble(message))
        transcript.scroll_end(animate=False)
        self._render_token_usage()

    async def _render_manage(self) -> None:
        manage_list = self.query_one("#manage-list", SelectionList)
        manage_list.clear_options()
        summaries = self.session.turn_summaries()
        if summaries:
            manage_list.add_options(
                (summary.label, summary.turn_id, summary.included)
                for summary in summaries
            )

    async def _append_status(self, content: str) -> Label:
        widget = Label(content, classes="status")
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.mount(widget)
        transcript.scroll_end(animate=False)
        return widget

    def _render_token_usage(self) -> None:
        usage = self.session.token_usage_totals()
        label = self.query_one("#token-usage", Label)
        model_label = self.model
        if usage.total_tokens:
            label.update(
                f"model {model_label} · tok {usage.total_tokens} · in {usage.prompt_tokens} · out {usage.completion_tokens}"
            )
        else:
            label.update(f"model {model_label} · tok 0")
