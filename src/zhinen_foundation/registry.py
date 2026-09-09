"""In-memory capability registry for the first vertical slice."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    capability_id: str
    version: str
    status: str
    provider: str
    prerequisites: tuple[str, ...] = ()


class CapabilityRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.capability_id in self._items:
            raise ValueError(f"capability already registered: {capability.capability_id}")
        self._items[capability.capability_id] = capability

    def get(self, capability_id: str) -> Capability:
        try:
            return self._items[capability_id]
        except KeyError as exc:
            raise KeyError(f"unknown capability: {capability_id}") from exc

    def can_activate(self, capability_id: str) -> bool:
        item = self.get(capability_id)
        return item.status not in {"retired", "deprecated"} and all(name in self._items for name in item.prerequisites)
