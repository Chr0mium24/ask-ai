from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from ask_ai.client import Message, ModelKey, TokenUsage

DATA_DIR_ENV = "ASK_DATA_DIR"
SESSION_FILE_SUFFIX = ".json"

Role = Literal["user", "assistant"]


def data_dir() -> Path:
    configured = os.environ.get(DATA_DIR_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "share" / "ask-ai"


def sessions_dir() -> Path:
    return data_dir() / "sessions"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class ChatMessage:
    id: str
    role: Role
    content: str
    turn_id: str
    included: bool = True
    model: ModelKey | None = None
    token_usage: TokenUsage | None = None
    created_at: str = field(default_factory=now_iso)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatMessage:
        role = data.get("role")
        if role not in {"user", "assistant"}:
            raise ValueError("invalid message role")

        model = data.get("model")
        if model not in {"flash", "pro"}:
            model = None

        raw_usage = data.get("token_usage")
        token_usage = (
            TokenUsage.from_dict(raw_usage) if isinstance(raw_usage, dict) else None
        )

        return cls(
            id=str(data.get("id") or new_id()),
            role=cast(Role, role),
            content=str(data.get("content") or ""),
            turn_id=str(data.get("turn_id") or new_id()),
            included=bool(data.get("included", True)),
            model=cast(ModelKey | None, model),
            token_usage=token_usage,
            created_at=str(data.get("created_at") or now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "turn_id": self.turn_id,
            "included": self.included,
            "model": self.model,
            "token_usage": self.token_usage.to_dict() if self.token_usage else None,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class TurnSummary:
    turn_id: str
    included: bool
    label: str


@dataclass(slots=True)
class ChatSession:
    id: str
    title: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    @classmethod
    def new(cls) -> ChatSession:
        timestamp = now_iso()
        return cls(
            id=new_id(),
            title="New chat",
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatSession:
        raw_messages = data.get("messages")
        messages: list[ChatMessage] = []
        if isinstance(raw_messages, list):
            for raw_message in raw_messages:
                if isinstance(raw_message, dict):
                    try:
                        messages.append(ChatMessage.from_dict(raw_message))
                    except ValueError:
                        continue

        return cls(
            id=str(data.get("id") or new_id()),
            title=str(data.get("title") or "New chat"),
            messages=messages,
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [message.to_dict() for message in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_user_message(self, content: str) -> str:
        turn_id = new_id()
        self.messages.append(
            ChatMessage(
                id=new_id(),
                role="user",
                content=content,
                turn_id=turn_id,
            )
        )
        if self.title == "New chat":
            self.title = summarize(content, 36)
        self.touch()
        return turn_id

    def add_assistant_message(
        self,
        content: str,
        *,
        turn_id: str,
        model: ModelKey,
        token_usage: TokenUsage | None = None,
    ) -> None:
        included = self.turn_included(turn_id)
        self.messages.append(
            ChatMessage(
                id=new_id(),
                role="assistant",
                content=content,
                turn_id=turn_id,
                included=included,
                model=model,
                token_usage=token_usage,
            )
        )
        self.touch()

    def clear(self) -> None:
        self.messages.clear()
        self.title = "New chat"
        self.touch()

    def context_messages(self, limit: int = 30) -> list[Message]:
        included_messages = [
            cast(Message, {"role": message.role, "content": message.content})
            for message in self.messages
            if message.included
        ]
        return included_messages[-limit:]

    def token_usage_totals(self) -> TokenUsage:
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        for message in self.messages:
            if message.token_usage is None:
                continue
            prompt_tokens += message.token_usage.prompt_tokens
            completion_tokens += message.token_usage.completion_tokens
            total_tokens += message.token_usage.total_tokens
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def set_turn_included(self, turn_id: str, included: bool) -> None:
        for message in self.messages:
            if message.turn_id == turn_id:
                message.included = included
        self.touch()

    def turn_included(self, turn_id: str) -> bool:
        turn_messages = [
            message for message in self.messages if message.turn_id == turn_id
        ]
        if not turn_messages:
            return True
        return all(message.included for message in turn_messages)

    def update_message(self, message_id: str, content: str) -> bool:
        for message in self.messages:
            if message.id == message_id:
                message.content = content
                if message.role == "user" and self._first_user_id() == message_id:
                    self.title = summarize(content, 36)
                self.touch()
                return True
        return False

    def get_message(self, message_id: str) -> ChatMessage | None:
        for message in self.messages:
            if message.id == message_id:
                return message
        return None

    def turn_summaries(self) -> list[TurnSummary]:
        summaries: list[TurnSummary] = []
        seen: set[str] = set()
        for message in self.messages:
            if message.turn_id in seen or message.role != "user":
                continue
            seen.add(message.turn_id)
            user_text = summarize(message.content, 52)
            assistant = next(
                (
                    candidate
                    for candidate in self.messages
                    if candidate.turn_id == message.turn_id
                    and candidate.role == "assistant"
                ),
                None,
            )
            assistant_text = summarize(assistant.content, 52) if assistant else "..."
            summaries.append(
                TurnSummary(
                    turn_id=message.turn_id,
                    included=self.turn_included(message.turn_id),
                    label=f"{user_text} -> {assistant_text}",
                )
            )
        return summaries

    def touch(self) -> None:
        self.updated_at = now_iso()

    def _first_user_id(self) -> str | None:
        for message in self.messages:
            if message.role == "user":
                return message.id
        return None


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or sessions_dir()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def list_sessions(self) -> list[ChatSession]:
        sessions: list[ChatSession] = []
        for path in self.root.glob(f"*{SESSION_FILE_SUFFIX}"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                sessions.append(ChatSession.from_dict(data))
        sessions.sort(key=lambda session: session.updated_at, reverse=True)
        return sessions

    def load(self, session_id: str) -> ChatSession | None:
        path = self.path_for(session_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return ChatSession.from_dict(data)

    def save(self, session: ChatSession) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.path_for(session.id)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(session.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(path)

    def create(self) -> ChatSession:
        session = ChatSession.new()
        self.save(session)
        return session

    def load_or_create_latest(self) -> ChatSession:
        sessions = self.list_sessions()
        if sessions:
            return sessions[0]
        return self.create()

    def path_for(self, session_id: str) -> Path:
        return self.root / f"{session_id}{SESSION_FILE_SUFFIX}"


def summarize(content: str, limit: int) -> str:
    summary = " ".join(content.strip().split())
    if not summary:
        return "..."
    if len(summary) <= limit:
        return summary
    return f"{summary[: limit - 1]}..."
