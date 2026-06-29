# ask-ai

A lightweight DeepSeek assistant for shell one-shot answers and in-terminal
multi-turn chat.

## Install

```bash
uv sync
```

For fish, install the `ask` wrapper:

```bash
uv run ask install
```

Then set your API key:

```fish
ask login
```

## Usage

Open the TUI chat:

```bash
ask
```

TUI sessions are saved under `~/.local/share/ask-ai/sessions`. The left pane
lists saved sessions; selecting one switches the active chat.

TUI controls:

```text
Tab
/clear
/model [flash|pro]
/sidebar 12-40
/quit
```

`Tab` switches between chat and manage mode. Manage mode shows a checklist of
conversation pairs. Checked pairs are included in
future context; unchecked pairs stay visible in the session but are dimmed and
ignored by future requests. Double-click a message in the chat to edit it.

Message mouse actions:

- Left click copies a message.
- Double-click edits a message.
- Shift+left click expands or collapses a long message.
- Right click toggles whether that turn is included in context.
- Ctrl+right click deletes that turn after confirmation.
- Shift+right click opens the message action menu.

The left pane has `New` and `Del` buttons for session creation and deletion.
Token usage is shown above the input. `Ctrl+C` clears the input without exiting;
`Ctrl+Z` restores the last cleared input.
Long messages are collapsed by default in the TUI; this does not change the saved
content or model context.
While the model is answering, the TUI keeps handling navigation, session
switching, folding, and commands.

One-shot prompt without saving context:

```bash
ask "解释一下 Python GIL"
```

One-shot and piped calls create a new saved session automatically, so the result
appears in the TUI session list. They still do not reuse prior history.

Use stdin as context:

```bash
git diff | ask "review this diff"
```

Choose a one-shot model:

```bash
ask --model pro "给我一个更强的推理版本"
```

Save or remove the API key:

```bash
ask login
ask logout
```

Install or remove the fish wrapper:

```bash
uv run ask install
ask uninstall
```

`DEEPSEEK_API_KEY` still works and takes precedence over the saved login config.

## Models

- `flash`: `deepseek-v4-flash`
- `pro`: `deepseek-v4-pro`

The TUI keeps multi-turn context in persistent sessions. One-shot CLI calls are
stateless.
