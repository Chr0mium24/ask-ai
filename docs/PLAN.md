# ask-ai Plan

## Goal

Build a lightweight DeepSeek assistant for fish/shell usage.

## Behavior

- `ask` opens a Textual TUI when there is no prompt and no piped stdin.
- `ask "..."` sends a one-shot request and prints a Rich-rendered markdown answer.
- `cmd | ask "..."` sends a one-shot request with stdin as context.
- `cmd | ask` sends stdin with a default analysis prompt.
- One-shot mode is stateless by design.
- Only the TUI keeps multi-turn context, and that context is saved in persistent
  session files.
- The TUI provides bottom buttons for switching between `deepseek-v4-flash` and
  `deepseek-v4-pro`.
- The TUI shows all saved sessions in a left sidebar and supports switching
  between them.
- The TUI supports `/clear` and `/quit`.
- `Tab` toggles between chat and manage mode.
- Manage mode shows conversation-pair checkboxes. Unchecked pairs remain visible
  but are excluded from future model context and rendered as dimmed messages.
- Double-clicking a message opens an editor for that message.
- The bottom composer shows Flash/Pro model buttons and current session token
  usage.
- `ask login` saves a DeepSeek API key to `~/.config/ask-ai/config.json` with
  `0600` permissions.
- `ask logout` deletes the saved API key.

## Architecture

- `ask_ai.client`: DeepSeek API client, model mapping, prompt assembly.
- `ask_ai.cli`: argparse entrypoint and one-shot/TUI dispatch.
- `ask_ai.sessions`: persistent session files and context inclusion logic.
- `ask_ai.tui`: Textual app with session sidebar, model tabs, transcript,
  manage view, and input.

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
