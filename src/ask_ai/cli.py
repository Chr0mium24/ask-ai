from __future__ import annotations

import argparse
import asyncio
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
    build_one_shot_messages,
    parse_model_key,
)


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


async def async_main() -> int:
    args = build_parser().parse_args()

    if args.version:
        print(_version())
        return 0

    prompt = " ".join(args.prompt).strip()
    piped_input = "" if args.tui or sys.stdin.isatty() else sys.stdin.read()

    if args.tui or (not prompt and not piped_input):
        from ask_ai.tui import AskApp

        app = AskApp(base_url=args.base_url, system_prompt=args.system_prompt)
        app.run()
        return 0

    try:
        model = parse_model_key(args.model)
        messages = build_one_shot_messages(prompt, piped_input)
        client = DeepSeekClient(base_url=args.base_url)
        answer = await client.complete(
            messages,
            model=model,
            system_prompt=args.system_prompt,
        )
    except (DeepSeekError, ValueError) as exc:
        Console(stderr=True).print(f"[red]error:[/red] {exc}")
        return 2

    console = Console()
    console.print(Markdown(answer))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ask",
        description=(
            "Ask DeepSeek from the shell. With no prompt and no stdin, opens the TUI."
        ),
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
    return parser


def _version() -> str:
    try:
        return version("ask-ai")
    except PackageNotFoundError:
        return "0.0.0"
