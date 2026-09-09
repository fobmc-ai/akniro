from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .state_machine import assert_transition


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectStore:
    def __init__(self, database: str | Path = "control-center.db") -> None:
        self.db = sqlite3.connect(database, check_same_thread=False)
        self._lock = threading.RLock()
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
        CREATE TABLE IF NOT EXISTS project_nodes (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, parent_id TEXT,
          name TEXT NOT NULL, node_type TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
          FOREIGN KEY(project_id) REFERENCES projects(id),
          FOREIGN KEY(parent_id) REFERENCES project_nodes(id)
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
        self._create_default_tree(project_id)
        self._audit(tenant_id, project_id, owner_id, "project.create", project_id, "success", {})
        self.db.commit()
        return self.get_project(project_id)

    def _create_default_tree(self, project_id: str) -> None:
        nodes = [
            ("overview", "00-项目总览", "section"), ("requirements", "01-需求", "section"),
            ("solution", "02-技术方案", "section"), ("architecture", "03-架构与 ADR", "section"),
            ("work", "04-开发任务", "section"), ("quality", "05-测试与证据", "section"),
            ("problems", "06-问题与 CAPA", "section"), ("release", "07-发布与维护", "section"),
            ("knowledge", "08-知识库", "section"),
        ]
        self.db.executemany("INSERT INTO project_nodes(id, project_id, name, node_type, sort_order) VALUES (?, ?, ?, ?, ?)", [(f"{project_id}:{node_id}", project_id, name, node_type, index) for index, (node_id, name, node_type) in enumerate(nodes)])

    def get_tree(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT id, parent_id, name, node_type, sort_order FROM project_nodes WHERE project_id = ? ORDER BY sort_order, name", (project_id,)).fetchall()
        by_parent: dict[str | None, list[dict[str, Any]]] = {}
        for row in rows:
            item = dict(row); item["children"] = []
            by_parent.setdefault(row["parent_id"], []).append(item)
        def attach(parent: str | None) -> list[dict[str, Any]]:
            items = by_parent.get(parent, [])
            for item in items:
                item["children"] = attach(item["id"])
            return items
        return attach(None)

    def get_project(self, project_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown project: {project_id}")
        result = dict(row)
        result["entities"] = [dict(item) for item in self.db.execute("SELECT * FROM entities WHERE project_id = ? ORDER BY entity_type, created_at", (project_id,))]
        for item in result["entities"]:
            item["payload"] = json.loads(item["payload"])
        return result

    def list_projects(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM projects ORDER BY updated_at DESC")]

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
