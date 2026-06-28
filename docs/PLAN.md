# ask-ai Plan

## Goal

Build a lightweight DeepSeek assistant for fish/shell usage.

## Behavior

- `ask` opens a Textual TUI when there is no prompt and no piped stdin.
- `ask "..."` sends a one-shot request and prints a Rich-rendered markdown answer.
- `cmd | ask "..."` sends a one-shot request with stdin as context.
- `cmd | ask` sends stdin with a default analysis prompt.
- One-shot mode is stateless by design.
- Only the TUI keeps multi-turn context, and that context is in memory for the running session.
- The TUI provides tabs for model switching between `deepseek-v4-flash` and `deepseek-v4-pro`.
- `ask login` saves a DeepSeek API key to `~/.config/ask-ai/config.json` with
  `0600` permissions.
- `ask logout` deletes the saved API key.

## Architecture

- `ask_ai.client`: DeepSeek API client, model mapping, prompt assembly.
- `ask_ai.cli`: argparse entrypoint and one-shot/TUI dispatch.
- `ask_ai.tui`: Textual app with model tabs, transcript, and input.

## Configuration

- `DEEPSEEK_API_KEY`: optional environment override for API calls.
- Saved login config: used when `DEEPSEEK_API_KEY` is not set.
- `DEEPSEEK_BASE_URL`: optional, defaults to `https://api.deepseek.com`.
- `ASK_MODEL`: optional one-shot default, `flash` or `pro`.
- `ASK_SYSTEM_PROMPT`: optional system prompt override.

## Validation

- Run static import checks through `uv run python -m compileall src`.
- Run command help/version checks.
- Run stdin path with missing API key to verify error handling.
- Run login/logout checks with `ASK_CONFIG_DIR` pointed at a temporary directory.
- If an API key is available, run one real one-shot request.
