from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import httpx

from ask_ai.config import load_api_key

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_SYSTEM_PROMPT = (
    "You are a concise terminal AI assistant. Match the user's language, "
    "be direct, and use markdown when it improves clarity."
)

ModelKey = Literal["flash", "pro"]

MODEL_IDS: dict[ModelKey, str] = {
    "flash": "deepseek-v4-flash",
    "pro": "deepseek-v4-pro",
}

MODEL_LABELS: dict[ModelKey, str] = {
    "flash": "Flash",
    "pro": "Pro",
}


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class DeepSeekError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TokenUsage:
        if data is None:
            return cls()
        prompt_tokens = _safe_int(data.get("prompt_tokens"))
        completion_tokens = _safe_int(data.get("completion_tokens"))
        total_tokens = _safe_int(data.get("total_tokens"))
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens
        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(slots=True, frozen=True)
class CompletionResult:
    content: str
    usage: TokenUsage = TokenUsage()


@dataclass(slots=True)
class DeepSeekClient:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 60.0

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("DEEPSEEK_API_KEY") or load_api_key()
        self.base_url = self.base_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        messages: list[Message],
        model: ModelKey = "flash",
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> str:
        result = await self.complete_with_usage(
            messages,
            model=model,
            system_prompt=system_prompt,
        )
        return result.content

    async def complete_with_usage(
        self,
        messages: list[Message],
        model: ModelKey = "flash",
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> CompletionResult:
        if not self.api_key:
            raise DeepSeekError(
                "No DeepSeek API key found. Run `ask login` or set DEEPSEEK_API_KEY."
            )

        payload_messages: list[Message] = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]
        payload = {
            "model": MODEL_IDS[model],
            "messages": payload_messages,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise DeepSeekError(
                f"DeepSeek API returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DeepSeekError(f"DeepSeek API request failed: {exc}") from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = TokenUsage.from_dict(data.get("usage"))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise DeepSeekError("DeepSeek API returned an unexpected response.") from exc

        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek API returned an empty response.")
        return CompletionResult(content=content.strip(), usage=usage)


def build_one_shot_messages(prompt: str, piped_input: str) -> list[Message]:
    prompt = prompt.strip()
    piped_input = piped_input.strip()

    if prompt and piped_input:
        content = (
            f"{prompt}\n\n"
            "Context from stdin:\n"
            "```text\n"
            f"{piped_input}\n"
            "```"
        )
    elif prompt:
        content = prompt
    elif piped_input:
        content = (
            "Analyze the following input and respond concisely.\n\n"
            "```text\n"
            f"{piped_input}\n"
            "```"
        )
    else:
        raise ValueError("prompt or piped_input is required")

    return [{"role": "user", "content": content}]


def parse_model_key(raw: str | None) -> ModelKey:
    if raw in MODEL_IDS:
        return raw  # type: ignore[return-value]
    valid = ", ".join(MODEL_IDS)
    raise ValueError(f"unknown model {raw!r}; expected one of: {valid}")


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:500] or response.reason_phrase

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        message = data.get("message")
        if isinstance(message, str):
            return message
    return str(data)[:500]


def _safe_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
