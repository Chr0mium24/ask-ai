from __future__ import annotations

import time
from typing import Literal

from textual.events import Click
from textual.message import Message as TextualMessage
from textual.widgets import Label, ListItem, Markdown

from ask_ai.sessions import ChatMessage, ChatSession

MessageAction = Literal["copy", "edit", "toggle", "delete", "collapse"]

COLLAPSE_CHAR_LIMIT = 900
COLLAPSE_LINE_LIMIT = 18
COLLAPSE_PREVIEW_CHARS = 520


class SessionItem(ListItem):
    class DeleteRequested(TextualMessage):
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    def __init__(self, session: ChatSession) -> None:
        super().__init__(Label(session.title), classes="session-item")
        self.session_id = session.id

    def on_click(self, event: Click) -> None:
        if event.button == 3 and event.ctrl:
            event.stop()
            self.post_message(self.DeleteRequested(self.session_id))


class MessageBubble(Markdown):
    class CopyRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    class EditRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    class ToggleRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    class DeleteRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    class CollapseRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    class MenuRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    def __init__(self, message: ChatMessage, *, collapsed: bool = False) -> None:
        classes = f"message {message.role}"
        if not message.included:
            classes += " ignored"
        content = _render_message_content(message.content, collapsed=collapsed)
        super().__init__(content, classes=classes)
        self.message_id = message.id
        self.collapsed = collapsed
        self._last_left_click_at = 0.0

    def on_click(self, event: Click) -> None:
        event.stop()

        if event.button == 1:
            if event.shift:
                self.post_message(self.CollapseRequested(self.message_id))
                return

            now = time.monotonic()
            if now - self._last_left_click_at <= 0.45:
                self.post_message(self.EditRequested(self.message_id))
            else:
                self.post_message(self.CopyRequested(self.message_id))
            self._last_left_click_at = now
            return

        if event.button != 3:
            return

        if event.ctrl:
            self.post_message(self.DeleteRequested(self.message_id))
        elif event.shift:
            self.post_message(self.MenuRequested(self.message_id))
        else:
            self.post_message(self.ToggleRequested(self.message_id))


def should_collapse(content: str) -> bool:
    return len(content) > COLLAPSE_CHAR_LIMIT or content.count("\n") >= COLLAPSE_LINE_LIMIT


def _render_message_content(content: str, *, collapsed: bool) -> str:
    if not collapsed:
        return content

    preview = content.strip()
    if len(preview) > COLLAPSE_PREVIEW_CHARS:
        preview = f"{preview[:COLLAPSE_PREVIEW_CHARS].rstrip()}..."
    lines = preview.splitlines()
    if len(lines) > 10:
        preview = "\n".join(lines[:10]).rstrip() + "\n..."
    return f"{preview}\n\n_[collapsed: shift+click or menu to expand]_"
