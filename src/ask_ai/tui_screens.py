from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea

from ask_ai.tui_widgets import MessageAction


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


class ConfirmScreen(ModalScreen[bool]):
    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: 52;
        background: $surface;
        border: solid $error;
        padding: 1;
    }

    #confirm-title {
        text-style: bold;
        height: 1;
    }

    #confirm-message {
        height: auto;
        margin: 1 0;
    }

    #confirm-actions {
        height: 3;
        align-horizontal: right;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, message: str, confirm_label: str = "Delete") -> None:
        super().__init__()
        self.title_text = title
        self.message = message
        self.confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(self.title_text, id="confirm-title")
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-actions"):
                yield Button("Cancel", id="cancel")
                yield Button(self.confirm_label, variant="error", id="confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)


class MessageActionScreen(ModalScreen[MessageAction | None]):
    CSS = """
    MessageActionScreen {
        align: center middle;
    }

    #message-menu {
        width: 34;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    #message-menu Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="message-menu"):
            yield Button("Copy", id="copy")
            yield Button("Edit", id="edit")
            yield Button("Toggle context", id="toggle")
            yield Button("Delete", variant="error", id="delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        if action in {"copy", "edit", "toggle", "delete"}:
            self.dismiss(action)  # type: ignore[arg-type]

    def action_cancel(self) -> None:
        self.dismiss(None)
