"""Append-only audit records for foundation operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    action: str
    actor: str
    target: str
    outcome: str
    correlation_id: str
    occurred_at: str
    details: dict[str, Any]


class AuditLog:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, *, action: str, actor: str, target: str, outcome: str, correlation_id: str, details: dict[str, Any] | None = None) -> AuditRecord:
        record = AuditRecord(str(uuid4()), action, actor, target, outcome, correlation_id, datetime.now(timezone.utc).isoformat(), details or {})
        self._records.append(record)
        return record

    def all(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [asdict(record) for record in self._records]
