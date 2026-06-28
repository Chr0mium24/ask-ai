from __future__ import annotations

import time
from collections.abc import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message as TextualMessage
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    SelectionList,
    TextArea,
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
from ask_ai.sessions import ChatMessage, ChatSession, SessionStore


class SessionItem(ListItem):
    def __init__(self, session: ChatSession) -> None:
        super().__init__(Label(session.title), classes="session-item")
        self.session_id = session.id


class MessageBubble(Markdown):
    class EditRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    def __init__(self, message: ChatMessage) -> None:
        classes = f"message {message.role}"
        if not message.included:
            classes += " ignored"
        super().__init__(message.content, classes=classes)
        self.message_id = message.id
        self._last_click_at = 0.0

    def on_click(self) -> None:
        now = time.monotonic()
        if now - self._last_click_at <= 0.45:
            self.post_message(self.EditRequested(self.message_id))
        self._last_click_at = now


class EditMessageScreen(ModalScreen[str | None]):
    CSS = """
    EditMessageScreen {
        align: center middle;
    }

    #edit-dialog {
        width: 70%;
        height: 60%;
        max-width: 100;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    #edit-body {
        height: 1fr;
    }

    #edit-actions {
        height: 3;
        align-horizontal: right;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-dialog"):
            yield TextArea(
                self.content,
                id="edit-body",
                show_line_numbers=False,
                soft_wrap=True,
            )
            with Horizontal(id="edit-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", variant="primary", id="save")

    def on_mount(self) -> None:
        self.query_one("#edit-body", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()

    def action_save(self) -> None:
        self.dismiss(self.query_one("#edit-body", TextArea).text)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AskApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #sidebar {
        width: 22;
        min-width: 16;
        border-right: solid $primary;
    }

    #new-session {
        height: 3;
        width: 100%;
    }

    #sessions {
        height: 1fr;
    }

    .session-item {
        height: 1;
    }

    #main {
        width: 1fr;
    }

    #transcript {
        height: 1fr;
        padding: 1;
    }

    #manage-list {
        height: 1fr;
        padding: 1;
    }

    .message {
        margin-bottom: 1;
        padding: 0 1;
    }

    .user {
        border-left: heavy $accent;
    }

    .assistant {
        border-left: heavy $success;
    }

    .ignored {
        color: $text-muted;
        border-left: heavy gray;
    }

    .status {
        color: $text-muted;
        padding: 0 1;
    }

    #composer {
        height: 3;
    }

    .model-button {
        width: 8;
    }

    #token-usage {
        width: 27;
        color: $text-muted;
        padding: 0 1;
        content-align: center middle;
    }

    #prompt {
        height: 3;
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("tab", "toggle_mode", "Toggle mode", show=False, priority=True),
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

    def compose(self) -> ComposeResult:
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Button("New", id="new-session")
                yield ListView(id="sessions")
            with Vertical(id="main"):
                yield VerticalScroll(id="transcript")
                yield SelectionList[str](id="manage-list")
                with Horizontal(id="composer"):
                    yield Button("Flash", id="model-flash", classes="model-button")
                    yield Button("Pro", id="model-pro", classes="model-button")
                    yield Label("", id="token-usage")
                    yield Input(placeholder="Message or /clear /quit", id="prompt")

    async def on_mount(self) -> None:
        await self._render_sessions()
        await self._render_active_view()
        self._render_model_buttons()
        self.query_one("#prompt", Input).focus()

    async def action_toggle_mode(self) -> None:
        self.manage_mode = not self.manage_mode
        await self._render_active_view()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "new-session":
            await self._new_session()
            return
        if button_id == "model-flash":
            self.model = "flash"
            self._render_model_buttons()
            return
        if button_id == "model-pro":
            self.model = "pro"
            self._render_model_buttons()
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

    async def on_message_bubble_edit_requested(
        self,
        event: MessageBubble.EditRequested,
    ) -> None:
        message = self.session.get_message(event.message_id)
        if message is None:
            return

        self.push_screen(
            EditMessageScreen(message.content),
            callback=lambda updated: self._queue_message_edit(
                event.message_id,
                updated,
            ),
        )

    def _queue_message_edit(self, message_id: str, updated: str | None) -> None:
        if updated is None:
            return
        self.run_worker(
            self._finish_message_edit(message_id, updated),
            exit_on_error=False,
        )

    async def _finish_message_edit(self, message_id: str, updated: str) -> None:
        self.session.update_message(message_id, updated)
        self.store.save(self.session)
        await self._render_sessions()
        await self._render_active_view()

    async def _handle_command(self, command: str) -> None:
        if command == "/clear":
            self.session.clear()
            self.store.save(self.session)
            self.manage_mode = False
            await self._render_sessions()
            await self._render_active_view()
            return

        if command == "/quit":
            self.exit()
            return

        if command == "/new":
            await self._new_session()
            return

        await self._append_status(f"unknown command: {command}")

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

    def _render_model_buttons(self) -> None:
        flash = self.query_one("#model-flash", Button)
        pro = self.query_one("#model-pro", Button)
        flash.variant = "primary" if self.model == "flash" else "default"
        pro.variant = "primary" if self.model == "pro" else "default"

    def _render_token_usage(self) -> None:
        usage = self.session.token_usage_totals()
        label = self.query_one("#token-usage", Label)
        if usage.total_tokens:
            label.update(
                f"tok {usage.total_tokens} in {usage.prompt_tokens} out {usage.completion_tokens}"
            )
        else:
            label.update("tok 0")
