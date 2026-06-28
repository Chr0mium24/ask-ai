from __future__ import annotations

from ask_ai.tui_screens import ConfirmScreen, EditMessageScreen, MessageActionScreen
from ask_ai.tui_widgets import MessageAction, MessageBubble, SessionItem


class AskActionsMixin:
    def on_session_item_delete_requested(
        self,
        event: SessionItem.DeleteRequested,
    ) -> None:
        self._confirm_delete_session(event.session_id)

    async def on_message_bubble_edit_requested(
        self,
        event: MessageBubble.EditRequested,
    ) -> None:
        self._open_message_editor(event.message_id)

    def on_message_bubble_copy_requested(
        self,
        event: MessageBubble.CopyRequested,
    ) -> None:
        self._copy_message(event.message_id)

    async def on_message_bubble_toggle_requested(
        self,
        event: MessageBubble.ToggleRequested,
    ) -> None:
        await self._toggle_message_turn(event.message_id)

    def on_message_bubble_delete_requested(
        self,
        event: MessageBubble.DeleteRequested,
    ) -> None:
        self._confirm_delete_message_turn(event.message_id)

    async def on_message_bubble_collapse_requested(
        self,
        event: MessageBubble.CollapseRequested,
    ) -> None:
        await self._toggle_message_collapse(event.message_id)

    def on_message_bubble_menu_requested(
        self,
        event: MessageBubble.MenuRequested,
    ) -> None:
        self.push_screen(
            MessageActionScreen(),
            callback=lambda action: self._handle_message_menu_action(
                event.message_id,
                action,
            ),
        )

    def _handle_message_menu_action(
        self,
        message_id: str,
        action: MessageAction | None,
    ) -> None:
        if action is None:
            return

        if action == "copy":
            self._copy_message(message_id)
            return
        if action == "edit":
            self._open_message_editor(message_id)
            return
        if action == "delete":
            self._confirm_delete_message_turn(message_id)
            return
        if action == "collapse":
            self.run_worker(
                self._toggle_message_collapse(message_id),
                exit_on_error=False,
            )
            return

        self.run_worker(
            self._toggle_message_turn(message_id),
            exit_on_error=False,
        )

    def _open_message_editor(self, message_id: str) -> None:
        message = self.session.get_message(message_id)
        if message is None:
            return

        self.push_screen(
            EditMessageScreen(message.content),
            callback=lambda updated: self._queue_message_edit(
                message_id,
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
        self.expanded_messages.discard(message_id)
        self.store.save(self.session)
        await self._render_sessions()
        await self._render_active_view()

    def _copy_message(self, message_id: str) -> None:
        message = self.session.get_message(message_id)
        if message is None:
            return
        self.copy_to_clipboard(message.content)
        self.notify("Copied")

    async def _toggle_message_turn(self, message_id: str) -> None:
        message = self.session.get_message(message_id)
        if message is None:
            return
        included = not self.session.turn_included(message.turn_id)
        self.session.set_turn_included(message.turn_id, included)
        self.store.save(self.session)
        await self._render_active_view()
        self.notify("Included in context" if included else "Ignored in context")

    def _confirm_delete_message_turn(self, message_id: str) -> None:
        message = self.session.get_message(message_id)
        if message is None:
            return
        self.push_screen(
            ConfirmScreen(
                "Delete conversation?",
                "This deletes the selected user/assistant turn from this session.",
            ),
            callback=lambda confirmed: self._queue_delete_message_turn(
                message.turn_id,
                confirmed,
            ),
        )

    def _queue_delete_message_turn(self, turn_id: str, confirmed: bool) -> None:
        if not confirmed:
            return
        self.run_worker(
            self._finish_delete_message_turn(turn_id),
            exit_on_error=False,
        )

    async def _finish_delete_message_turn(self, turn_id: str) -> None:
        if self.session.delete_turn(turn_id):
            self.store.save(self.session)
            self.expanded_messages = {
                message.id for message in self.session.messages
            } & self.expanded_messages
            await self._render_sessions()
            await self._render_active_view()

    async def _toggle_message_collapse(self, message_id: str) -> None:
        if message_id in self.expanded_messages:
            self.expanded_messages.remove(message_id)
        else:
            self.expanded_messages.add(message_id)
        await self._render_chat()

    def _confirm_delete_session(self, session_id: str) -> None:
        self.push_screen(
            ConfirmScreen(
                "Delete session?",
                "This deletes the selected session file and cannot be undone.",
            ),
            callback=lambda confirmed: self._queue_delete_session(
                session_id,
                confirmed,
            ),
        )

    def _queue_delete_session(self, session_id: str, confirmed: bool) -> None:
        if not confirmed:
            return
        self.run_worker(
            self._finish_delete_session(session_id),
            exit_on_error=False,
        )

    async def _finish_delete_session(self, session_id: str) -> None:
        if not self.store.delete(session_id):
            return

        if self.session.id == session_id:
            self.session = self.store.load_or_create_latest()
            self.manage_mode = False
        await self._render_sessions()
        await self._render_active_view()
