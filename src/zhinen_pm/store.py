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
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, display_name TEXT NOT NULL,
          role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS project_members (
          project_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL,
          PRIMARY KEY(project_id, user_id),
          FOREIGN KEY(project_id) REFERENCES projects(id), FOREIGN KEY(user_id) REFERENCES users(id)
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
        CREATE TABLE IF NOT EXISTS backlog_items (
          project_id TEXT NOT NULL, id TEXT NOT NULL, master_refs TEXT NOT NULL,
          title TEXT NOT NULL, area TEXT NOT NULL, status TEXT NOT NULL,
          owner_id TEXT NOT NULL, placeholder INTEGER NOT NULL DEFAULT 0,
          target_release TEXT NOT NULL, dependencies TEXT NOT NULL,
          design_goal TEXT NOT NULL, acceptance_criteria TEXT NOT NULL,
          test_plan TEXT NOT NULL, evidence_links TEXT NOT NULL,
          risks TEXT NOT NULL, rollback_plan TEXT NOT NULL,
          revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          PRIMARY KEY(project_id, id), FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS sync_queue (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
          direction TEXT NOT NULL, object_type TEXT NOT NULL, object_id TEXT NOT NULL,
          idempotency_key TEXT NOT NULL UNIQUE, payload TEXT NOT NULL, status TEXT NOT NULL,
          reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS entity_links (
          project_id TEXT NOT NULL, from_id TEXT NOT NULL, to_id TEXT NOT NULL,
          link_type TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(project_id, from_id, to_id, link_type), FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, recipient_id TEXT NOT NULL,
          kind TEXT NOT NULL, message TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
          FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS machine_objects (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
          object_type TEXT NOT NULL, parent_id TEXT, name TEXT NOT NULL, owner_id TEXT NOT NULL,
          payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'DRAFT',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS machine_snapshots (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, machine_id TEXT NOT NULL,
          revision INTEGER NOT NULL, payload TEXT NOT NULL, created_by TEXT NOT NULL,
          created_at TEXT NOT NULL, FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id, entity_type);
        CREATE INDEX IF NOT EXISTS idx_audit_project ON audit(project_id, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_backlog_project ON backlog_items(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_sync_project ON sync_queue(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_machine_project ON machine_objects(project_id, object_type);
        """)
        self.db.commit()

    def _audit(self, tenant_id: str, project_id: str | None, actor_id: str, action: str, target_id: str, outcome: str, details: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), tenant_id, project_id, actor_id, action, target_id, outcome, json.dumps(details, ensure_ascii=False), now()))

    def create_project(self, *, project_id: str, tenant_id: str, name: str, kind: str, owner_id: str) -> dict[str, Any]:
        timestamp = now()
        self.db.execute("INSERT OR IGNORE INTO users(id, tenant_id, display_name, role) VALUES (?, ?, ?, 'owner')", (owner_id, tenant_id, owner_id))
        self.db.execute("INSERT INTO projects VALUES (?, ?, ?, ?, 'ACTIVE', ?, 1, ?, ?)", (project_id, tenant_id, name, kind, owner_id, timestamp, timestamp))
        self.db.execute("INSERT INTO project_members(project_id, user_id, role) VALUES (?, ?, 'owner')", (project_id, owner_id))
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
            ("implementation", "09-总纲实施路线", "section"),
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

    def add_node(self, *, project_id: str, node_id: str, name: str, node_type: str = "section", parent_id: str | None = None, sort_order: int = 0) -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone():
            raise KeyError(f"unknown project: {project_id}")
        if parent_id and not self.db.execute("SELECT 1 FROM project_nodes WHERE id = ? AND project_id = ?", (parent_id, project_id)).fetchone():
            raise KeyError("parent node not found in project")
        self.db.execute("INSERT INTO project_nodes(id, project_id, parent_id, name, node_type, sort_order) VALUES (?, ?, ?, ?, ?, ?)", (node_id, project_id, parent_id, name, node_type, sort_order))
        self.db.commit()
        return {"id": node_id, "project_id": project_id, "parent_id": parent_id, "name": name, "node_type": node_type, "sort_order": sort_order, "children": []}

    def get_actor(self, actor_id: str, tenant_id: str, project_id: str | None = None) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM users WHERE id = ? AND tenant_id = ? AND active = 1", (actor_id, tenant_id)).fetchone()
        if not row:
            raise PermissionError("PM-AUTH-004: unknown actor")
        projects = {x[0] for x in self.db.execute("SELECT project_id FROM project_members WHERE user_id = ?", (actor_id,))}
        if project_id and projects and project_id not in projects:
            raise PermissionError("PM-AUTH-002: project scope denied")
        return {"actor_id": row["id"], "role": row["role"], "tenant_id": row["tenant_id"], "project_ids": projects}

    def list_users(self, tenant_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT id, tenant_id, display_name, role, active FROM users WHERE tenant_id = ? ORDER BY id", (tenant_id,))]

    def create_user(self, *, user_id: str, tenant_id: str, display_name: str, role: str = "viewer") -> dict[str, Any]:
        if role not in {"viewer", "engineer", "reviewer", "qa", "owner", "ai"}:
            raise ValueError(f"invalid role: {role}")
        self.db.execute("INSERT INTO users(id, tenant_id, display_name, role) VALUES (?, ?, ?, ?)", (user_id, tenant_id, display_name, role))
        self.db.commit()
        return dict(self.db.execute("SELECT id, tenant_id, display_name, role, active FROM users WHERE id = ?", (user_id,)).fetchone())

    def add_member(self, *, project_id: str, user_id: str, role: str) -> dict[str, Any]:
        if role not in {"viewer", "engineer", "reviewer", "qa", "owner", "ai"}:
            raise ValueError(f"invalid role: {role}")
        project = self.db.execute("SELECT tenant_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        user = self.db.execute("SELECT tenant_id FROM users WHERE id = ? AND active = 1", (user_id,)).fetchone()
        if not project or not user or project["tenant_id"] != user["tenant_id"]:
            raise PermissionError("PM-AUTH-006: user and project tenant mismatch")
        self.db.execute("INSERT INTO project_members(project_id, user_id, role) VALUES (?, ?, ?) ON CONFLICT(project_id, user_id) DO UPDATE SET role = excluded.role", (project_id, user_id, role))
        self.db.commit()
        return {"project_id": project_id, "user_id": user_id, "role": role}

    def list_members(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT m.project_id, m.user_id, m.role, u.display_name FROM project_members m JOIN users u ON u.id = m.user_id WHERE m.project_id = ? ORDER BY m.user_id", (project_id,))]

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

    def import_backlog(self, *, project_id: str, items: list[dict[str, Any]], actor_id: str) -> int:
        project = self.db.execute("SELECT tenant_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise KeyError(f"unknown project: {project_id}")
        implementation_node = f"{project_id}:implementation"
        if not self.db.execute("SELECT 1 FROM project_nodes WHERE id = ?", (implementation_node,)).fetchone():
            next_order = self.db.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM project_nodes WHERE project_id = ?", (project_id,)).fetchone()[0]
            self.db.execute("INSERT INTO project_nodes(id, project_id, name, node_type, sort_order) VALUES (?, ?, ?, ?, ?)", (implementation_node, project_id, "09-总纲实施路线", "section", next_order))
        timestamp = now()
        inserted = 0
        for item in items:
            required = ["id", "title", "area", "status", "owner", "targetRelease", "designGoal", "acceptanceCriteria", "testPlan", "rollbackPlan"]
            missing = [key for key in required if key not in item]
            if missing:
                raise ValueError(f"backlog item missing fields: {', '.join(missing)}")
            values = (project_id, item["id"], json.dumps(item.get("masterPlanRefs", []), ensure_ascii=False), item["title"], item["area"], item["status"], item["owner"], int(bool(item.get("placeholder", False))), item["targetRelease"], json.dumps(item.get("dependencies", []), ensure_ascii=False), item["designGoal"], json.dumps(item["acceptanceCriteria"], ensure_ascii=False), item["testPlan"], json.dumps(item.get("evidenceLinks", []), ensure_ascii=False), json.dumps(item.get("risks", []), ensure_ascii=False), item["rollbackPlan"], timestamp, timestamp)
            cursor = self.db.execute("INSERT OR IGNORE INTO backlog_items(project_id, id, master_refs, title, area, status, owner_id, placeholder, target_release, dependencies, design_goal, acceptance_criteria, test_plan, evidence_links, risks, rollback_plan, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            inserted += cursor.rowcount
        self._audit(project["tenant_id"], project_id, actor_id, "backlog.import", project_id, "success", {"items": len(items), "inserted": inserted})
        self.db.commit()
        return inserted

    def list_backlog(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM backlog_items WHERE project_id = ?"
        args: list[Any] = [project_id]
        if status:
            query += " AND status = ?"; args.append(status)
        query += " ORDER BY id"
        rows = self.db.execute(query, args).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            for field in ("master_refs", "dependencies", "acceptance_criteria", "evidence_links", "risks"):
                item[field] = json.loads(item[field])
            item["placeholder"] = bool(item["placeholder"])
            result.append(item)
        return result

    def enqueue_sync(self, *, sync_id: str, project_id: str, tenant_id: str, direction: str, object_type: str, object_id: str, idempotency_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        if direction not in {"PULL_SNAPSHOT", "PUSH_APPROVED"}:
            raise ValueError("invalid sync direction")
        if direction == "PUSH_APPROVED" and not payload.get("approvalId"):
            raise PermissionError("PM-SYNC-001: push requires human approvalId")
        timestamp = now()
        self.db.execute("INSERT OR IGNORE INTO sync_queue VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', '', ?, ?)", (sync_id, project_id, tenant_id, direction, object_type, object_id, idempotency_key, json.dumps(payload, ensure_ascii=False), timestamp, timestamp))
        self.db.commit()
        row = self.db.execute("SELECT * FROM sync_queue WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        result = dict(row); result["payload"] = json.loads(result["payload"]); return result

    def list_sync_queue(self, project_id: str) -> list[dict[str, Any]]:
        result = []
        for row in self.db.execute("SELECT * FROM sync_queue WHERE project_id = ? ORDER BY created_at", (project_id,)):
            item = dict(row); item["payload"] = json.loads(item["payload"]); result.append(item)
        return result

    def project_stats(self, project_id: str) -> dict[str, Any]:
        rows = self.db.execute("SELECT entity_type, status, COUNT(*) AS count FROM entities WHERE project_id = ? GROUP BY entity_type, status", (project_id,)).fetchall()
        by_type: dict[str, dict[str, int]] = {}
        for row in rows:
            by_type.setdefault(row["entity_type"], {})[row["status"]] = row["count"]
        return {"projectId": project_id, "entities": by_type, "backlog": len(self.list_backlog(project_id)), "syncQueue": len(self.list_sync_queue(project_id)), "links": len(self.list_links(project_id))}

    def list_audit(self, project_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit WHERE project_id = ? ORDER BY occurred_at DESC LIMIT ?", (project_id, limit))]

    def notify(self, *, notification_id: str, project_id: str, recipient_id: str, kind: str, message: str) -> dict[str, Any]:
        self.db.execute("INSERT OR IGNORE INTO notifications VALUES (?, ?, ?, ?, ?, 0, ?)", (notification_id, project_id, recipient_id, kind, message, now()))
        self.db.commit()
        return dict(self.db.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone())

    def list_notifications(self, recipient_id: str, project_id: str | None = None) -> list[dict[str, Any]]:
        if project_id:
            rows = self.db.execute("SELECT * FROM notifications WHERE recipient_id = ? AND project_id = ? ORDER BY created_at DESC", (recipient_id, project_id))
        else:
            rows = self.db.execute("SELECT * FROM notifications WHERE recipient_id = ? ORDER BY created_at DESC", (recipient_id,))
        return [dict(row) for row in rows]

    def backup(self, destination: str) -> str:
        target = sqlite3.connect(destination)
        try:
            self.db.backup(target)
        finally:
            target.close()
        return destination

    def create_machine_object(self, *, object_id: str, project_id: str, tenant_id: str, object_type: str, name: str, owner_id: str, payload: dict[str, Any] | None = None, parent_id: str | None = None) -> dict[str, Any]:
        allowed = {"machine", "module", "device", "tag", "alarm", "recipe"}
        if object_type not in allowed:
            raise ValueError(f"unsupported machine object: {object_type}")
        if not self.db.execute("SELECT 1 FROM projects WHERE id = ? AND tenant_id = ?", (project_id, tenant_id)).fetchone():
            raise KeyError("project not found in tenant")
        if parent_id and not self.db.execute("SELECT 1 FROM machine_objects WHERE id = ? AND project_id = ?", (parent_id, project_id)).fetchone():
            raise KeyError("machine parent not found in project")
        timestamp = now()
        self.db.execute("INSERT INTO machine_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'DRAFT', ?, ?)", (object_id, project_id, tenant_id, object_type, parent_id, name, owner_id, json.dumps(payload or {}, ensure_ascii=False), timestamp, timestamp))
        self.db.commit()
        return self.get_machine_object(object_id)

    def get_machine_object(self, object_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM machine_objects WHERE id = ?", (object_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown machine object: {object_id}")
        result = dict(row); result["payload"] = json.loads(result["payload"]); return result

    def list_machine_objects(self, project_id: str, object_type: str | None = None) -> list[dict[str, Any]]:
        if object_type:
            rows = self.db.execute("SELECT * FROM machine_objects WHERE project_id = ? AND object_type = ? ORDER BY id", (project_id, object_type))
        else:
            rows = self.db.execute("SELECT * FROM machine_objects WHERE project_id = ? ORDER BY object_type, id", (project_id,))
        result = []
        for row in rows:
            item = dict(row); item["payload"] = json.loads(item["payload"]); result.append(item)
        return result

    def snapshot_machine(self, *, snapshot_id: str, project_id: str, machine_id: str, created_by: str) -> dict[str, Any]:
        machine = self.get_machine_object(machine_id)
        if machine["project_id"] != project_id or machine["object_type"] != "machine":
            raise ValueError("snapshot target must be a machine in project")
        objects = self.list_machine_objects(project_id)
        payload = {"machine": machine, "objects": objects}
        self.db.execute("INSERT INTO machine_snapshots VALUES (?, ?, ?, ?, ?, ?, ?)", (snapshot_id, project_id, machine_id, machine["revision"], json.dumps(payload, ensure_ascii=False), created_by, now()))
        self.db.commit()
        return self.get_snapshot(snapshot_id)

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM machine_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown snapshot: {snapshot_id}")
        result = dict(row); result["payload"] = json.loads(result["payload"]); return result

    def backlog_readiness(self, project_id: str) -> list[dict[str, Any]]:
        items = self.list_backlog(project_id)
        status = {item["id"]: item["status"] for item in items}
        ready_states = {"VALIDATED", "RELEASED"}
        result = []
        for item in items:
            missing = [dependency for dependency in item["dependencies"] if status.get(dependency) not in ready_states]
            result.append({"id": item["id"], "status": item["status"], "placeholder": item["placeholder"], "ready": not missing and item["status"] not in {"DEFERRED", "BLOCKED", "FAILED"}, "blockedBy": missing})
        return result

    def update_machine_object(self, *, object_id: str, name: str | None, payload: dict[str, Any] | None, expected_revision: int) -> dict[str, Any]:
        current = self.get_machine_object(object_id)
        if current["revision"] != expected_revision:
            raise RuntimeError("PM-CONFLICT-001: machine object revision conflict")
        self.db.execute("UPDATE machine_objects SET name = ?, payload = ?, revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?", (name or current["name"], json.dumps(payload if payload is not None else current["payload"], ensure_ascii=False), now(), object_id, expected_revision))
        self.db.commit()
        return self.get_machine_object(object_id)

    def diff_snapshots(self, left_id: str, right_id: str) -> dict[str, Any]:
        left = self.get_snapshot(left_id); right = self.get_snapshot(right_id)
        left_map = {x["id"]: x for x in left["payload"]["objects"]}; right_map = {x["id"]: x for x in right["payload"]["objects"]}
        return {"left": left_id, "right": right_id, "added": sorted(set(right_map) - set(left_map)), "removed": sorted(set(left_map) - set(right_map)), "changed": sorted(key for key in set(left_map) & set(right_map) if left_map[key] != right_map[key])}

    def release_gate(self, release_id: str) -> dict[str, Any]:
        release = self.get_entity(release_id)
        if release["entity_type"] != "release":
            raise ValueError("gate target must be release")
        links = self.list_links(release["project_id"], release_id)
        linked = {x["to_id"] if x["from_id"] == release_id else x["from_id"] for x in links}
        evidence = [self.get_entity(x) for x in linked if self.db.execute("SELECT entity_type FROM entities WHERE id = ?", (x,)).fetchone() and self.db.execute("SELECT entity_type FROM entities WHERE id = ?", (x,)).fetchone()[0] == "evidence"]
        passed = [x for x in evidence if x["status"] == "VALIDATED"]
        approval = bool(release["payload"].get("approvalId"))
        return {"releaseId": release_id, "ready": bool(passed and approval), "validatedEvidence": [x["id"] for x in passed], "approval": approval, "missing": (["validated evidence"] if not passed else []) + (["human approval"] if not approval else [])}

    def link_entities(self, *, project_id: str, from_id: str, to_id: str, link_type: str) -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM entities WHERE id = ? AND project_id = ?", (from_id, project_id)).fetchone() or not self.db.execute("SELECT 1 FROM entities WHERE id = ? AND project_id = ?", (to_id, project_id)).fetchone():
            raise KeyError("entity link target not found in project")
        self.db.execute("INSERT OR IGNORE INTO entity_links VALUES (?, ?, ?, ?, ?)", (project_id, from_id, to_id, link_type, now()))
        self.db.commit()
        return {"project_id": project_id, "from_id": from_id, "to_id": to_id, "link_type": link_type}

    def list_links(self, project_id: str, entity_id: str | None = None) -> list[dict[str, Any]]:
        if entity_id:
            rows = self.db.execute("SELECT * FROM entity_links WHERE project_id = ? AND (from_id = ? OR to_id = ?) ORDER BY created_at", (project_id, entity_id, entity_id))
        else:
            rows = self.db.execute("SELECT * FROM entity_links WHERE project_id = ? ORDER BY created_at", (project_id,))
        return [dict(row) for row in rows]

    def search(self, project_id: str, query: str) -> list[dict[str, Any]]:
        needle = f"%{query}%"
        rows = self.db.execute("SELECT id, entity_type, title, status, owner_id, updated_at FROM entities WHERE project_id = ? AND (id LIKE ? OR title LIKE ?) ORDER BY updated_at DESC", (project_id, needle, needle)).fetchall()
        return [dict(row) for row in rows]

    def transition_sync(self, sync_id: str, target: str, reason: str = "") -> dict[str, Any]:
        allowed = {"QUEUED": {"APPLIED", "CONFLICT", "FAILED"}, "CONFLICT": {"QUEUED", "FAILED"}, "FAILED": {"QUEUED"}, "APPLIED": set()}
        row = self.db.execute("SELECT * FROM sync_queue WHERE id = ?", (sync_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown sync: {sync_id}")
        if target not in allowed.get(row["status"], set()):
            raise ValueError(f"PM-SYNC-002: invalid transition {row['status']}->{target}")
        self.db.execute("UPDATE sync_queue SET status = ?, reason = ?, updated_at = ? WHERE id = ?", (target, reason, now(), sync_id))
        self.db.commit()
        result = dict(self.db.execute("SELECT * FROM sync_queue WHERE id = ?", (sync_id,)).fetchone()); result["payload"] = json.loads(result["payload"]); return result

    def get_sync(self, sync_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM sync_queue WHERE id = ?", (sync_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown sync: {sync_id}")
        result = dict(row); result["payload"] = json.loads(result["payload"]); return result

    def create_entity(self, *, entity_id: str, entity_type: str, project_id: str, tenant_id: str, title: str, owner_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM projects WHERE id = ? AND tenant_id = ?", (project_id, tenant_id)).fetchone():
            raise KeyError("project not found in tenant")
        status = {"requirement": "DRAFT", "design_goal": "DRAFT", "work_item": "PLANNED", "issue": "OPEN", "adr": "PROPOSED", "test_case": "DRAFT", "knowledge": "DRAFT", "release": "DRAFT", "test_plan": "DRAFT", "test_run": "QUEUED", "evidence": "DRAFT", "tool_validation": "DRAFT", "artifact": "DRAFT", "parameter_snapshot": "DRAFT", "maintenance": "OPEN"}.get(entity_type)
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

    def list_entities(self, project_id: str, entity_type: str | None = None) -> list[dict[str, Any]]:
        if entity_type:
            rows = self.db.execute("SELECT * FROM entities WHERE project_id = ? AND entity_type = ? ORDER BY updated_at DESC", (project_id, entity_type)).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM entities WHERE project_id = ? ORDER BY updated_at DESC", (project_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row); item["payload"] = json.loads(item["payload"]); result.append(item)
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
