# ask-ai Experiments

## 2026-06-28

### Planned checks

- `uv run python -m compileall src`
- `uv run ask --help`
- `uv run ask --version`
- `printf 'hello' | uv run ask --model flash`
- Optional real API request if `DEEPSEEK_API_KEY` is present.

### Results

- `uv run python -m compileall src`: passed.
- `uv run ask --help`: passed and showed the expected CLI options.
- `uv run ask --version`: passed and returned `0.1.0`.
- `printf 'hello' | env -u DEEPSEEK_API_KEY uv run ask --model flash`: passed;
  exited with code 2 and printed `DEEPSEEK_API_KEY is not set.`
- Textual headless check with `AskApp.run_test()`: passed; model tab changed from
  Flash to Pro and `action_clear_chat()` completed.
- Real DeepSeek API request: skipped because `DEEPSEEK_API_KEY` was not present in
  the environment.
