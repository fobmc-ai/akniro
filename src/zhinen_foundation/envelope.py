"""Versioned command/event metadata shared by platform modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


@dataclass(frozen=True)
class MessageEnvelope:
    messageId: str
    messageType: str
    schemaVersion: str
    actor: str
    tenantId: str
    siteId: str
    machineId: str
    correlationId: str
    causationId: str | None
    occurredAt: str
    idempotencyKey: str
    payload: dict[str, Any]
    kind: Literal["command", "event"]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_message(kind: Literal["command", "event"], message_type: str, payload: dict[str, Any], *, actor: str, tenant_id: str, site_id: str, machine_id: str, correlation_id: str | None = None, causation_id: str | None = None, idempotency_key: str | None = None, schema_version: str = "0.1") -> MessageEnvelope:
    now = datetime.now(timezone.utc).isoformat()
    return MessageEnvelope(
        messageId=str(uuid4()), messageType=message_type, schemaVersion=schema_version,
        actor=actor, tenantId=tenant_id, siteId=site_id, machineId=machine_id,
        correlationId=correlation_id or str(uuid4()), causationId=causation_id,
        occurredAt=now, idempotencyKey=idempotency_key or str(uuid4()),
        payload=payload, kind=kind,
    )
