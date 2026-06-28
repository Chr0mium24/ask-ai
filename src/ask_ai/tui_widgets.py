from __future__ import annotations

import time
from typing import Literal

from textual.events import Click
from textual.message import Message as TextualMessage
from textual.widgets import Label, ListItem, Markdown

from ask_ai.sessions import ChatMessage, ChatSession

MessageAction = Literal["copy", "edit", "toggle", "delete"]


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

    class MenuRequested(TextualMessage):
        def __init__(self, message_id: str) -> None:
            super().__init__()
            self.message_id = message_id

    def __init__(self, message: ChatMessage) -> None:
        classes = f"message {message.role}"
        if not message.included:
            classes += " ignored"
        super().__init__(message.content, classes=classes)
        self.message_id = message.id
        self._last_left_click_at = 0.0

    def on_click(self, event: Click) -> None:
        event.stop()

        if event.button == 1:
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
