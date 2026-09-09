"""At-least-once event outbox with deterministic retry behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .envelope import MessageEnvelope


@dataclass
class OutboxEntry:
    message: MessageEnvelope
    published_at: str | None = None
    attempts: int = 0
    last_error: str | None = None


class Outbox:
    def __init__(self) -> None:
        self._entries: dict[str, OutboxEntry] = {}

    def append(self, message: MessageEnvelope) -> OutboxEntry:
        return self._entries.setdefault(message.messageId, OutboxEntry(message))

    def pending(self) -> tuple[OutboxEntry, ...]:
        return tuple(entry for entry in self._entries.values() if entry.published_at is None)

    def publish_pending(self, publisher: Callable[[MessageEnvelope], None]) -> int:
        published = 0
        for entry in self.pending():
            entry.attempts += 1
            try:
                publisher(entry.message)
            except Exception as exc:  # publisher failures are recorded for retry/diagnostics
                entry.last_error = str(exc)
                continue
            entry.published_at = datetime.now(timezone.utc).isoformat()
            entry.last_error = None
            published += 1
        return published
