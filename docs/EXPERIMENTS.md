# ask-ai Experiments

## 2026-06-28

### Planned checks

- `uv run python -m compileall src`
- `uv run ask --help`
- `uv run ask --version`
- `printf 'hello' | uv run ask --model flash`
- `ASK_CONFIG_DIR=$(mktemp -d) uv run ask login test-key`
- Login config readback and logout using a temporary config directory.
- Optional real API request if `DEEPSEEK_API_KEY` is present.

### Results

- `uv run python -m compileall src`: passed.
- `uv run ask --help`: passed and showed the expected CLI options.
- `uv run ask --version`: passed and returned `0.1.0`.
- `printf 'hello' | env -u DEEPSEEK_API_KEY uv run ask --model flash`: passed;
  exited with code 2 and printed `DEEPSEEK_API_KEY is not set.`
- Historical Textual headless check with `AskApp.run_test()`: passed; the
  then-current model tab changed from Flash to Pro and `action_clear_chat()`
  completed.
- Real DeepSeek API request: skipped because `DEEPSEEK_API_KEY` was not present in
  the environment.

### 2026-06-28 login update

- `uv run python -m compileall src`: passed.
- `uv run ask --help`: passed and listed local commands `ask login` and
  `ask logout`.
- `uv run ask --version`: passed and returned `0.1.0`.
- Temporary login check with `ASK_CONFIG_DIR=$(mktemp -d)`: passed.
- Saved config permissions check: passed with mode `600`.
- Config readback through `load_api_key()` and `DeepSeekClient()`: passed.
- Temporary logout check: passed and removed `config.json`.
- `fish -ic 'type -q ask; and ask --version'`: passed and returned `0.1.0`.
- Textual headless check with `AskApp.run_test()`: passed after the login update.
- Missing key path with empty `ASK_CONFIG_DIR`: passed; printed a clear message to
  run `ask login` or set `DEEPSEEK_API_KEY`.

### 2026-06-28 TUI entrypoint fix

- `uv run python -m compileall src`: passed.
- `uv run ask --version`: passed and returned `0.1.0`.
- `uv run ask --help`: passed.
- Missing key one-shot path with empty `ASK_CONFIG_DIR`: passed.
- TUI dispatch regression with monkeypatched `AskApp.run()`: passed; calling
  `cli.main()` with no prompt exited with code `0` and did not raise nested
  event-loop errors.
- Textual headless check with `AskApp.run_test()`: passed.
- `fish -ic 'type -q ask; and ask --version'`: passed and returned `0.1.0`.

### 2026-06-28 persistent TUI sessions

- `uv run python -m compileall src`: passed.
- `uv run ask --version`: passed and returned `0.1.0`.
- `uv run ask --help`: passed.
- Missing key one-shot path with empty `ASK_CONFIG_DIR`: passed.
- Session persistence with temporary `ASK_DATA_DIR`: passed; saved sessions
  reloaded and excluded turns stayed excluded.
- Historical Textual state flow with temporary `ASK_DATA_DIR`: passed; sidebar
  mounted, `/new` created a session, the then-current `/manage` view showed
  checked conversation pairs, excluded turns left context, and `/clear` cleared
  messages.
- `fish -ic 'type -q ask; and ask --version'`: passed and returned `0.1.0`.
- TUI regression for session switch, filtered context, and message edit handler:
  passed with a fake client and temporary `ASK_DATA_DIR`.
- TUI fake client error path: passed; failed requests leave the input usable and
  show the error status without a secondary UI exception.
- TUI no-argument dispatch regression: passed with monkeypatched `AskApp.run()`.

### 2026-06-28 TUI controls update

- `uv run python -m compileall src`: passed.
- `uv run ask --help`: passed.
- `uv run ask --version`: passed and returned `0.1.0`.
- `TokenUsage.from_dict()` with missing `total_tokens`: passed and fell back to
  prompt plus completion tokens.
- Missing key one-shot path with empty `ASK_CONFIG_DIR`: passed.
- Session token usage persistence with temporary `ASK_DATA_DIR`: passed.
- TUI controls regression with temporary `ASK_DATA_DIR`: passed; bottom Flash/Pro
  buttons switched models, `New` created a session, `Tab` toggled manage mode,
  unchecked turns stayed out of context, token usage updated after a fake
  response, and callback-based editing updated a dimmed message without
  `NoActiveWorker`.
- TUI fake client error path: passed.
- `fish -ic 'type -q ask; and ask --version'`: passed and returned `0.1.0`.
- TUI no-argument dispatch regression: passed with monkeypatched `AskApp.run()`.

### 2026-06-28 TUI file split and actions

- `uv run python -m compileall src`: passed.
- TUI refactor regression with temporary `ASK_DATA_DIR`: passed; `/model`,
  `/sidebar`, `Ctrl+C`, `Ctrl+Z`, left-click copy, right-click context toggle,
  edit callback, confirmed conversation deletion, and confirmed session deletion
  all behaved as expected.
- Mouse-specific regression: passed; Ctrl+right-click opened delete confirmation,
  and Shift+right-click opened the message action menu.
- Final smoke checks passed: `uv run ask --help`, `uv run ask --version`,
  missing-key one-shot path, fish wrapper version check, and no-argument TUI
  dispatch regression.

### 2026-06-28 CLI session persistence

- One-shot persistence test with fake client and temporary `ASK_DATA_DIR`:
  passed; saved a new session with user content, assistant content, model, and
  token usage without reusing existing history.

### 2026-06-28 long message collapse

- `uv run python -m compileall src`: passed.
- Collapse regression with temporary `ASK_DATA_DIR`: passed; long messages
  rendered collapsed by default, Shift+left-click expanded them, explicit toggle
  collapsed them again, and left-click copied the full original content.

### 2026-06-29 nonblocking TUI requests

- `uv run python -m compileall src`: passed.
- Slow-client worker regression with temporary `ASK_DATA_DIR`: passed; while the
  fake model was waiting, the TUI toggled manage mode and changed `/model`
  without waiting for the response.
- Session-switch worker regression: passed; a response completed into the
  original session after switching to a new session.
- Worker error regression: passed; failed requests restored pending state and
  kept the user message in the session.
