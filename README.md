# ask-ai

A lightweight DeepSeek assistant for shell one-shot answers and in-terminal
multi-turn chat.

## Install

```bash
uv sync
```

For fish, add the command wrapper:

```fish
function ask
    command uv run --project /home/cr/Codes/ask-ai ask $argv
end
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
/quit
```

`Tab` switches between chat and manage mode. Manage mode shows a checklist of
conversation pairs. Checked pairs are included in
future context; unchecked pairs stay visible in the session but are dimmed and
ignored by future requests. Double-click a message in the chat to edit it.

The left pane has a `New` button for creating a session. The bottom bar contains
Flash/Pro model buttons and token usage for the current session.

One-shot prompt without saving context:

```bash
ask "解释一下 Python GIL"
```

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

`DEEPSEEK_API_KEY` still works and takes precedence over the saved login config.

## Models

- `flash`: `deepseek-v4-flash`
- `pro`: `deepseek-v4-pro`

The TUI keeps multi-turn context in persistent sessions. One-shot CLI calls are
stateless.
