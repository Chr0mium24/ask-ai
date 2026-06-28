from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static, Tab, Tabs

from ask_ai.client import (
    DEFAULT_BASE_URL,
    DEFAULT_SYSTEM_PROMPT,
    MODEL_LABELS,
    DeepSeekClient,
    DeepSeekError,
    Message,
    ModelKey,
)


class AskApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #model-tabs {
        dock: top;
    }

    #transcript {
        height: 1fr;
        padding: 1;
        border: solid $primary;
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

    .status {
        color: $text-muted;
    }

    #prompt {
        dock: bottom;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
    ]

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        super().__init__()
        self.client = DeepSeekClient(base_url=base_url)
        self.system_prompt = system_prompt
        self.model: ModelKey = "flash"
        self.history: list[Message] = []
        self.pending = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Tabs(
            Tab("Flash", id="flash"),
            Tab("Pro", id="pro"),
            id="model-tabs",
        )
        with VerticalScroll(id="transcript"):
            yield Static(
                "DeepSeek TUI chat. Ctrl+L clears this in-memory session.",
                classes="message status",
            )
        yield Input(
            placeholder="Ask DeepSeek...",
            id="prompt",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "ask"
        self.sub_title = f"model: {MODEL_LABELS[self.model]}"
        self.query_one("#prompt", Input).focus()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        tab_id = event.tab.id
        if tab_id in MODEL_LABELS:
            self.model = tab_id  # type: ignore[assignment]
            self.sub_title = f"model: {MODEL_LABELS[self.model]}"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt or self.pending:
            return

        input_widget = self.query_one("#prompt", Input)
        input_widget.value = ""
        input_widget.disabled = True
        self.pending = True
        request_model = self.model

        self.history.append({"role": "user", "content": prompt})
        await self._append_user(prompt)
        status = await self._append_status(
            f"Asking DeepSeek {MODEL_LABELS[request_model]}..."
        )

        try:
            answer = await self.client.complete(
                self.history[-30:],
                model=request_model,
                system_prompt=self.system_prompt,
            )
            self.history.append({"role": "assistant", "content": answer})
            await status.remove()
            await self._append_assistant(answer, request_model)
        except DeepSeekError as exc:
            await status.update(f"error: {exc}")
        finally:
            input_widget.disabled = False
            input_widget.focus()
            self.pending = False

    async def action_clear_chat(self) -> None:
        self.history.clear()
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.remove_children()
        await transcript.mount(
            Static("Session cleared.", classes="message status")
        )

    async def _append_user(self, content: str) -> None:
        await self._append_static(f"**You**\n\n{content}", "message user")

    async def _append_assistant(self, content: str, model: ModelKey) -> None:
        await self._append_markdown(
            f"**DeepSeek {MODEL_LABELS[model]}**\n\n{content}",
            "message assistant",
        )

    async def _append_status(self, content: str) -> Static:
        widget = Static(content, classes="message status")
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.mount(widget)
        transcript.scroll_end(animate=False)
        return widget

    async def _append_static(self, content: str, classes: str) -> None:
        widget = Static(content, classes=classes)
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.mount(widget)
        transcript.scroll_end(animate=False)

    async def _append_markdown(self, content: str, classes: str) -> None:
        widget = Markdown(content, classes=classes)
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.mount(widget)
        transcript.scroll_end(animate=False)
