from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from importlib.metadata import PackageNotFoundError, version

from rich.console import Console
from rich.markdown import Markdown

from ask_ai.client import (
    DEFAULT_BASE_URL,
    DEFAULT_SYSTEM_PROMPT,
    MODEL_IDS,
    DeepSeekClient,
    DeepSeekError,
    ModelKey,
    TokenUsage,
    build_one_shot_messages,
    parse_model_key,
)
from ask_ai.config import config_path, delete_api_key, save_api_key
from ask_ai.install import InstallError, install_fish_function, uninstall_fish_function
from ask_ai.sessions import SessionStore


def main() -> None:
    raise SystemExit(run())


def run() -> int:
    args = build_parser().parse_args()

    if args.version:
        print(_version())
        return 0

    command_result = _handle_local_command(args.prompt, force=args.force)
    if command_result is not None:
        return command_result
    if args.force:
        Console(stderr=True).print(
            "[red]error:[/red] --force is only supported by ask install/uninstall"
        )
        return 2

    prompt = " ".join(args.prompt).strip()
    piped_input = "" if args.tui or sys.stdin.isatty() else sys.stdin.read()

    if args.tui or (not prompt and not piped_input):
        from ask_ai.tui import AskApp

        app = AskApp(base_url=args.base_url, system_prompt=args.system_prompt)
        app.run()
        return 0

    return asyncio.run(_run_one_shot(args, prompt, piped_input))


async def _run_one_shot(
    args: argparse.Namespace,
    prompt: str,
    piped_input: str,
) -> int:
    try:
        model = parse_model_key(args.model)
        messages = build_one_shot_messages(prompt, piped_input)
        client = DeepSeekClient(base_url=args.base_url)
        result = await client.complete_with_usage(
            messages,
            model=model,
            system_prompt=args.system_prompt,
        )
    except (DeepSeekError, ValueError) as exc:
        Console(stderr=True).print(f"[red]error:[/red] {exc}")
        return 2

    console = Console()
    console.print(Markdown(result.content))
    try:
        _save_one_shot_session(
            messages[0]["content"],
            result.content,
            model,
            result.usage,
        )
    except OSError as exc:
        Console(stderr=True).print(
            f"[yellow]warning:[/yellow] could not save session: {exc}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ask",
        description=(
            "Ask DeepSeek from the shell. With no prompt and no stdin, opens the TUI."
        ),
        epilog="Local commands: ask install, ask uninstall, ask login, ask logout",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="one-shot prompt; omitted with no stdin to launch the TUI",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=sorted(MODEL_IDS),
        default=os.environ.get("ASK_MODEL", "flash"),
        help="model for one-shot answers: flash or pro",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        help="DeepSeek API base URL",
    )
    parser.add_argument(
        "--system-prompt",
        default=os.environ.get("ASK_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        help="system prompt used for requests",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="launch the TUI even when stdin is present",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show version and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def _handle_local_command(prompt_parts: list[str], force: bool = False) -> int | None:
    if not prompt_parts:
        return None

    command, *rest = prompt_parts
    if command == "install":
        return _install(rest, force=force)
    if command == "uninstall":
        return _uninstall(rest, force=force)
    if command == "login":
        return _login(rest)
    if command == "logout":
        return _logout(rest)
    return None


def _install(args: list[str], force: bool = False) -> int:
    console = Console()
    err_console = Console(stderr=True)

    if args:
        err_console.print("[red]error:[/red] usage: ask install [--force]")
        return 2

    try:
        result = install_fish_function(force=force)
    except InstallError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        return 2

    if not result.changed:
        console.print(f"Fish function already installed at [bold]{result.path}[/bold].")
        return 0

    action = "Replaced" if result.replaced else "Installed"
    console.print(f"{action} fish function at [bold]{result.path}[/bold].")
    console.print(
        "It runs "
        f"[bold]uv run --project {result.project_dir} ask[/bold] "
        "with your arguments."
    )
    console.print("Open a new fish shell if an older ask function is already loaded.")
    return 0


def _uninstall(args: list[str], force: bool = False) -> int:
    console = Console()
    err_console = Console(stderr=True)

    if args:
        err_console.print("[red]error:[/red] usage: ask uninstall [--force]")
        return 2

    try:
        result = uninstall_fish_function(force=force)
    except InstallError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        return 2

    if result.removed:
        console.print(f"Removed fish function at [bold]{result.path}[/bold].")
        console.print("Open a new fish shell or run `functions -e ask` if needed.")
    else:
        console.print(f"No fish function found at [bold]{result.path}[/bold].")
    return 0


def _login(args: list[str]) -> int:
    console = Console()
    err_console = Console(stderr=True)

    if len(args) > 1:
        err_console.print("[red]error:[/red] usage: ask login [api-key]")
        return 2

    if args:
        api_key = args[0]
    else:
        api_key = getpass.getpass("DeepSeek API key: ")

    try:
        path = save_api_key(api_key)
    except ValueError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        return 2

    console.print(f"Saved DeepSeek API key to [bold]{path}[/bold].")
    console.print("The file permissions were set to 600.")
    return 0


def _logout(args: list[str]) -> int:
    console = Console()
    err_console = Console(stderr=True)

    if args:
        err_console.print("[red]error:[/red] usage: ask logout")
        return 2

    if delete_api_key():
        console.print(f"Deleted DeepSeek API key from [bold]{config_path()}[/bold].")
    else:
        console.print(f"No saved API key found at [bold]{config_path()}[/bold].")
    return 0


def _save_one_shot_session(
    user_content: str,
    assistant_content: str,
    model: ModelKey,
    token_usage: TokenUsage,
) -> None:
    store = SessionStore()
    session = store.create()
    turn_id = session.add_user_message(user_content)
    session.add_assistant_message(
        assistant_content,
        turn_id=turn_id,
        model=model,
        token_usage=token_usage,
    )
    store.save(session)


def _version() -> str:
    try:
        return version("ask-ai")
    except PackageNotFoundError:
        return "0.0.0"
