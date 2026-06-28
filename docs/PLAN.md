# ask-ai Plan

## Goal

Build a lightweight DeepSeek assistant for fish/shell usage.

## Behavior

- `ask` opens a Textual TUI when there is no prompt and no piped stdin.
- `ask "..."` sends a one-shot request and prints a Rich-rendered markdown answer.
- `cmd | ask "..."` sends a one-shot request with stdin as context.
- `cmd | ask` sends stdin with a default analysis prompt.
- One-shot mode is stateless by design.
- One-shot and piped calls create a new saved session after a successful answer,
  but still do not reuse prior history.
- Only the TUI keeps multi-turn context, and that context is saved in persistent
  session files.
- The TUI uses `/model [flash|pro]` to switch between `deepseek-v4-flash` and
  `deepseek-v4-pro`.
- The TUI shows all saved sessions in a left sidebar and supports switching
  between them.
- The TUI supports `/clear` and `/quit`.
- The TUI supports `/sidebar 12-40` to adjust sidebar width.
- `Tab` toggles between chat and manage mode.
- Manage mode shows conversation-pair checkboxes. Unchecked pairs remain visible
  but are excluded from future model context and rendered as dimmed messages.
- Double-clicking a message opens an editor for that message.
- Left-clicking a message copies it; right-click toggles context inclusion;
  Ctrl+right-click deletes the turn after confirmation; Shift+right-click opens
  a message action menu.
- Long messages are collapsed by default; Shift+left-click or the message menu
  toggles expansion without changing saved content or context.
- Session deletion requires confirmation.
- `Ctrl+C` clears the input, and `Ctrl+Z` restores the last cleared input.
- Current session token usage is shown above the input.
- `ask login` saves a DeepSeek API key to `~/.config/ask-ai/config.json` with
  `0600` permissions.
- `ask logout` deletes the saved API key.

## Architecture

- `ask_ai.client`: DeepSeek API client, model mapping, prompt assembly.
- `ask_ai.cli`: argparse entrypoint and one-shot/TUI dispatch.
- `ask_ai.sessions`: persistent session files and context inclusion logic.
- `ask_ai.tui`: Textual app with session sidebar, transcript, manage view, and
  input.
- `ask_ai.tui_actions`: message and session actions.
- `ask_ai.tui_screens`: edit, confirm, and message-action modal screens.
- `ask_ai.tui_widgets`: message and session widgets.
- `ask_ai.tui_styles`: Textual CSS for the main app.

## Configuration

- `DEEPSEEK_API_KEY`: optional environment override for API calls.
- Saved login config: used when `DEEPSEEK_API_KEY` is not set.
- `DEEPSEEK_BASE_URL`: optional, defaults to `https://api.deepseek.com`.
- `ASK_MODEL`: optional one-shot default, `flash` or `pro`.
- `ASK_SYSTEM_PROMPT`: optional system prompt override.
- `ASK_DATA_DIR`: optional data root override for session tests and custom
  storage locations.

## Validation

- Run static import checks through `uv run python -m compileall src`.
- Run command help/version checks.
- Run stdin path with missing API key to verify error handling.
- Run login/logout checks with `ASK_CONFIG_DIR` pointed at a temporary directory.
- Run session persistence checks with `ASK_DATA_DIR` pointed at a temporary
  directory.
- If an API key is available, run one real one-shot request.

## 2026-06-28 TUI Entrypoint Fix

Problem: `ask` with no arguments entered the TUI path from inside
`asyncio.run()`, while Textual's `App.run()` also starts its own event loop.

Plan:

- Keep command parsing and TUI dispatch synchronous.
- Use `asyncio.run()` only for one-shot DeepSeek API calls.
- Add a regression check that monkeypatches `AskApp.run()` and calls `cli.main()`
  with no prompt.

## 2026-06-28 Persistent TUI Sessions

Plan:

- Add JSON-backed session storage under `~/.local/share/ask-ai/sessions`.
- Replace the single-column chat with a compact session sidebar plus main chat.
- Remove Header/Footer and message role labels from the chat UI.
- Preserve model switching and one-shot CLI behavior.
- Implement `/clear`, `/quit`, a visible `New` session button, and `Tab` for
  manage mode.
- Use a checklist manage view for conversation pairs and persist inclusion state.
- Render excluded messages as dimmed in the chat view.
- Add double-click editing for saved messages.

## 2026-06-28 TUI Controls Update

Plan:

- Replace `/manage` with a global `Tab` key mode switch.
- Move Flash/Pro selection to the bottom composer.
- Add current session token usage in the bottom composer.
- Narrow the left sidebar and add a visible `New` session button.
- Replace `push_screen_wait()` editing with a callback-based modal flow so edits
  work from normal UI event handlers.

## 2026-06-28 TUI File Split And Actions

Plan:

- Split TUI code into app, actions, screens, widgets, and style modules.
- Replace Flash/Pro buttons with `/model [flash|pro]`.
- Move token usage above the input.
- Add `/sidebar 12-40` for adjustable sidebar width.
- Add confirmed session deletion and confirmed conversation-turn deletion.
- Add message mouse actions: left-click copy, double-click edit, right-click
  toggle context inclusion, Ctrl+right-click delete, Shift+right-click menu.
- Bind `Ctrl+C` to clear input and `Ctrl+Z` to restore the last cleared input.

## 2026-06-28 CLI Session Persistence

Plan:

- Keep one-shot CLI and piped calls stateless for request context.
- After a successful one-shot response, create a new persistent session containing
  the current user request, assistant response, selected model, and token usage.
- Ensure those sessions are visible in the TUI sidebar.

## 2026-06-28 Long Message Collapse

Plan:

- Collapse long messages by default in the TUI while preserving full saved
  content and full context behavior.
- Use Shift+left-click and the message menu to expand/collapse a message.
- Keep left-click copy behavior copying the full original content.
