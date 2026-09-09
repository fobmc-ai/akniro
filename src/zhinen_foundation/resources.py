"""Deterministic in-memory resource lease rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ResourceLease:
    lease_id: str
    resource: str
    holder: str
    priority: str
    mode: str
    expires_at: datetime


class ResourceLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, ResourceLease] = {}

    def acquire(self, lease: ResourceLease, *, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        self.expire(current)
        conflicts = [x for x in self._leases.values() if x.resource == lease.resource and (x.mode == "exclusive" or lease.mode == "exclusive")]
        if conflicts:
            raise RuntimeError(f"resource unavailable: {lease.resource}")
        if lease.expires_at <= current:
            raise ValueError("lease must expire in the future")
        self._leases[lease.lease_id] = lease

    def release(self, lease_id: str) -> None:
        self._leases.pop(lease_id, None)

    def expire(self, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        for lease_id, lease in list(self._leases.items()):
            if lease.expires_at <= current:
                del self._leases[lease_id]

    def active(self) -> tuple[ResourceLease, ...]:
        self.expire()
        return tuple(self._leases.values())
