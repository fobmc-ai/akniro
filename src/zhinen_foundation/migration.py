"""Explicit, ordered and idempotent project migrations."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any


Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationError(RuntimeError):
    pass


class MigrationRegistry:
    def __init__(self) -> None:
        self._migrations: dict[tuple[str, str], Migration] = {}

    def register(self, from_version: str, to_version: str, migration: Migration) -> None:
        key = (from_version, to_version)
        if key in self._migrations:
            raise MigrationError(f"migration already registered: {from_version}->{to_version}")
        self._migrations[key] = migration

    def migrate(self, project: dict[str, Any], target_version: str) -> dict[str, Any]:
        result = deepcopy(project)
        current = result.get("schemaVersion")
        if not isinstance(current, str):
            raise MigrationError("project schemaVersion is required")
        while current != target_version:
            candidates = [(to_version, fn) for (from_version, to_version), fn in self._migrations.items() if from_version == current]
            if len(candidates) != 1:
                raise MigrationError(f"no unique migration path from {current} to {target_version}")
            next_version, migration = candidates[0]
            result = migration(deepcopy(result))
            if result.get("schemaVersion") != next_version:
                raise MigrationError(f"migration {current}->{next_version} did not set schemaVersion")
            current = next_version
        return result
