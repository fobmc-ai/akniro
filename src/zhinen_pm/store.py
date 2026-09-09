from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .state_machine import assert_transition


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectStore:
    def __init__(self, database: str | Path = "control-center.db") -> None:
        self.db = sqlite3.connect(database)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
          kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE',
          owner_id TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entities (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
          entity_type TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL,
          owner_id TEXT NOT NULL, payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS audit (
          id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT,
          actor_id TEXT NOT NULL, action TEXT NOT NULL, target_id TEXT NOT NULL,
          outcome TEXT NOT NULL, details TEXT NOT NULL, occurred_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id, entity_type);
        CREATE INDEX IF NOT EXISTS idx_audit_project ON audit(project_id, occurred_at);
        """)
        self.db.commit()

    def _audit(self, tenant_id: str, project_id: str | None, actor_id: str, action: str, target_id: str, outcome: str, details: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), tenant_id, project_id, actor_id, action, target_id, outcome, json.dumps(details, ensure_ascii=False), now()))

    def create_project(self, *, project_id: str, tenant_id: str, name: str, kind: str, owner_id: str) -> dict[str, Any]:
        timestamp = now()
        self.db.execute("INSERT INTO projects VALUES (?, ?, ?, ?, 'ACTIVE', ?, 1, ?, ?)", (project_id, tenant_id, name, kind, owner_id, timestamp, timestamp))
        self._audit(tenant_id, project_id, owner_id, "project.create", project_id, "success", {})
        self.db.commit()
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown project: {project_id}")
        result = dict(row)
        result["entities"] = [dict(item) for item in self.db.execute("SELECT * FROM entities WHERE project_id = ? ORDER BY entity_type, created_at", (project_id,))]
        for item in result["entities"]:
            item["payload"] = json.loads(item["payload"])
        return result

    def create_entity(self, *, entity_id: str, entity_type: str, project_id: str, tenant_id: str, title: str, owner_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM projects WHERE id = ? AND tenant_id = ?", (project_id, tenant_id)).fetchone():
            raise KeyError("project not found in tenant")
        status = {"requirement": "DRAFT", "work_item": "PLANNED", "issue": "OPEN"}.get(entity_type)
        if status is None:
            raise ValueError(f"unsupported PM-0 entity: {entity_type}")
        timestamp = now()
        self.db.execute("INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)", (entity_id, project_id, tenant_id, entity_type, title, status, owner_id, json.dumps(payload or {}, ensure_ascii=False), timestamp, timestamp))
        self._audit(tenant_id, project_id, owner_id, f"{entity_type}.create", entity_id, "success", {})
        self.db.commit()
        return self.get_entity(entity_id)

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown entity: {entity_id}")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def transition(self, *, entity_id: str, target: str, actor_id: str, expected_revision: int) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown entity: {entity_id}")
        if row["revision"] != expected_revision:
            raise RuntimeError("PM-CONFLICT-001: revision conflict")
        assert_transition(row["entity_type"], row["status"], target)
        timestamp = now()
        self.db.execute("UPDATE entities SET status = ?, revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?", (target, timestamp, entity_id, expected_revision))
        self._audit(row["tenant_id"], row["project_id"], actor_id, f"{row['entity_type']}.transition", entity_id, "success", {"from": row["status"], "to": target})
        self.db.commit()
        return self.get_entity(entity_id)

    def audit(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit WHERE project_id = ? ORDER BY occurred_at", (project_id,))]

    def close(self) -> None:
        self.db.close()
