# ask-ai

A lightweight DeepSeek assistant for shell one-shot answers and in-terminal
multi-turn chat.

## Install

```bash
uv sync
```

Set your API key:

```fish
set -gx DEEPSEEK_API_KEY "sk-..."
```

For fish, after installing the project or running from this directory:

```fish
function ask
    command uv run --project /home/cr/Codes/ask-ai ask $argv
end
```

## Usage

Open the TUI chat:

```bash
ask
```

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

## Models

- `flash`: `deepseek-v4-flash`
- `pro`: `deepseek-v4-pro`

The TUI keeps multi-turn context only for the current running session. One-shot
CLI calls are stateless.
