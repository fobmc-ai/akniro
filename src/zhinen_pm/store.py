from __future__ import annotations

import json
import hashlib
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
        CREATE TABLE IF NOT EXISTS event_outbox (
          id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
          message_type TEXT NOT NULL, schema_version TEXT NOT NULL, actor_id TEXT NOT NULL,
          correlation_id TEXT NOT NULL, causation_id TEXT, idempotency_key TEXT NOT NULL UNIQUE,
          payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED', attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
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
        CREATE TABLE IF NOT EXISTS artifact_manifests (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, artifact_type TEXT NOT NULL,
          source_uri TEXT NOT NULL, content_hash TEXT NOT NULL, artifact_revision TEXT NOT NULL,
          toolchain_version TEXT NOT NULL, target_environment TEXT NOT NULL, sensitivity TEXT NOT NULL,
          owner_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'DRAFT', created_at TEXT NOT NULL,
          FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id, entity_type);
        CREATE INDEX IF NOT EXISTS idx_audit_project ON audit(project_id, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_backlog_project ON backlog_items(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_sync_project ON sync_queue(project_id, status);
        CREATE INDEX IF NOT EXISTS idx_event_project ON event_outbox(project_id, status, created_at);
        CREATE INDEX IF NOT EXISTS idx_machine_project ON machine_objects(project_id, object_type);
        """)
        artifact_columns = {row[1] for row in self.db.execute("PRAGMA table_info(artifact_manifests)")}
        if "revision" not in artifact_columns:
            self.db.execute("ALTER TABLE artifact_manifests ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
        self.db.commit()

    def _audit(self, tenant_id: str, project_id: str | None, actor_id: str, action: str, target_id: str, outcome: str, details: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), tenant_id, project_id, actor_id, action, target_id, outcome, json.dumps(details, ensure_ascii=False), now()))

    def _emit_event(self, *, tenant_id: str, project_id: str, message_type: str, actor_id: str, payload: dict[str, Any], correlation_id: str, idempotency_key: str, causation_id: str | None = None) -> None:
        timestamp = now()
        self.db.execute("INSERT OR IGNORE INTO event_outbox VALUES (?, ?, ?, ?, '0.1', ?, ?, ?, ?, ?, 'QUEUED', 0, '', ?, ?)", (str(uuid4()), tenant_id, project_id, message_type, actor_id, correlation_id, causation_id, idempotency_key, json.dumps(payload, ensure_ascii=False, sort_keys=True), timestamp, timestamp))

    def list_events(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM event_outbox WHERE project_id = ?"
        args: list[Any] = [project_id]
        if status:
            query += " AND status = ?"; args.append(status)
        query += " ORDER BY created_at"
        result = []
        for row in self.db.execute(query, args):
            item = dict(row); item["payload"] = json.loads(item["payload"]); result.append(item)
        return result

    def transition_event(self, event_id: str, target: str, actor_id: str, reason: str = "") -> dict[str, Any]:
        event = self.db.execute("SELECT * FROM event_outbox WHERE id = ?", (event_id,)).fetchone()
        if not event:
            raise KeyError(f"unknown event: {event_id}")
        allowed = {"QUEUED": {"PUBLISHED", "FAILED"}, "FAILED": {"QUEUED"}, "PUBLISHED": set()}
        if target not in allowed.get(event["status"], set()):
            raise ValueError(f"PM-EVENT-001: invalid transition {event['status']}->{target}")
        timestamp = now()
        attempts = event["attempts"] + (1 if target in {"PUBLISHED", "FAILED"} else 0)
        self.db.execute("UPDATE event_outbox SET status = ?, attempts = ?, last_error = ?, updated_at = ? WHERE id = ?", (target, attempts, reason if target == "FAILED" else "", timestamp, event_id))
        self._audit(event["tenant_id"], event["project_id"], actor_id, "event.publish", event_id, "success" if target == "PUBLISHED" else target.lower(), {"target": target, "reason": reason})
        self.db.commit()
        result = dict(self.db.execute("SELECT * FROM event_outbox WHERE id = ?", (event_id,)).fetchone()); result["payload"] = json.loads(result["payload"]); return result

    def create_project(self, *, project_id: str, tenant_id: str, name: str, kind: str, owner_id: str) -> dict[str, Any]:
        timestamp = now()
        self.db.execute("INSERT OR IGNORE INTO users(id, tenant_id, display_name, role) VALUES (?, ?, ?, 'owner')", (owner_id, tenant_id, owner_id))
        self.db.execute("INSERT INTO projects VALUES (?, ?, ?, ?, 'ACTIVE', ?, 1, ?, ?)", (project_id, tenant_id, name, kind, owner_id, timestamp, timestamp))
        self.db.execute("INSERT INTO project_members(project_id, user_id, role) VALUES (?, ?, 'owner')", (project_id, owner_id))
        self._create_default_tree(project_id)
        self._audit(tenant_id, project_id, owner_id, "project.create", project_id, "success", {})
        self._emit_event(tenant_id=tenant_id, project_id=project_id, message_type="pm.project.created", actor_id=owner_id, payload={"projectId": project_id, "kind": kind}, correlation_id=project_id, idempotency_key=f"project.created:{project_id}:1")
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
        self._audit(project["tenant_id"], project_id, user_id, "project.member.update", user_id, "success", {"role": role})
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

    def list_projects(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        if tenant_id:
            return [dict(row) for row in self.db.execute("SELECT * FROM projects WHERE tenant_id = ? ORDER BY updated_at DESC", (tenant_id,))]
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

    def reconcile_backlog(self, *, project_id: str, items: list[dict[str, Any]], actor_id: str) -> int:
        """Refresh source-controlled planning state without replacing project-owned fields."""
        project = self.db.execute("SELECT tenant_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise KeyError(f"unknown project: {project_id}")
        timestamp = now()
        updated = 0
        for item in items:
            cursor = self.db.execute("UPDATE backlog_items SET status = ?, placeholder = ?, evidence_links = ?, updated_at = ? WHERE project_id = ? AND id = ?", (item["status"], int(bool(item.get("placeholder", False))), json.dumps(item.get("evidenceLinks", []), ensure_ascii=False), timestamp, project_id, item["id"]))
            updated += cursor.rowcount
        self._audit(project["tenant_id"], project_id, actor_id, "backlog.reconcile", project_id, "success", {"items": len(items), "updated": updated})
        if updated:
            self._emit_event(tenant_id=project["tenant_id"], project_id=project_id, message_type="pm.backlog.reconciled", actor_id=actor_id, payload={"updated": updated, "source": "implementation-backlog"}, correlation_id=f"backlog:{project_id}", idempotency_key=f"backlog.reconciled:{project_id}:{timestamp}")
        self.db.commit()
        return updated

    def enqueue_sync(self, *, sync_id: str, project_id: str, tenant_id: str, direction: str, object_type: str, object_id: str, idempotency_key: str, payload: dict[str, Any], actor_id: str = "system") -> dict[str, Any]:
        if direction not in {"PULL_SNAPSHOT", "PUSH_APPROVED"}:
            raise ValueError("invalid sync direction")
        if direction == "PUSH_APPROVED" and not payload.get("approvalId"):
            raise PermissionError("PM-SYNC-001: push requires human approvalId")
        timestamp = now()
        cursor = self.db.execute("INSERT OR IGNORE INTO sync_queue VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', '', ?, ?)", (sync_id, project_id, tenant_id, direction, object_type, object_id, idempotency_key, json.dumps(payload, ensure_ascii=False), timestamp, timestamp))
        if cursor.rowcount == 1:
            self._audit(tenant_id, project_id, actor_id, "sync.enqueue", sync_id, "success", {"direction": direction, "objectId": object_id})
            self._emit_event(tenant_id=tenant_id, project_id=project_id, message_type="pm.sync.queued", actor_id=actor_id, payload={"syncId": sync_id, "direction": direction, "objectType": object_type, "objectId": object_id, "status": "QUEUED"}, correlation_id=sync_id, idempotency_key=f"sync.queued:{sync_id}")
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

    def control_plane_health(self, project_id: str) -> dict[str, Any]:
        """Expose deterministic, project-scoped operations signals for the management center."""
        sync_rows = self.list_sync_queue(project_id)
        unread = self.db.execute("SELECT COUNT(*) FROM notifications WHERE project_id = ? AND read = 0", (project_id,)).fetchone()[0]
        audit_count = self.db.execute("SELECT COUNT(*) FROM audit WHERE project_id = ?", (project_id,)).fetchone()[0]
        event_rows = self.list_events(project_id)
        page_count = self.db.execute("PRAGMA page_count").fetchone()[0]
        page_size = self.db.execute("PRAGMA page_size").fetchone()[0]
        return {"projectId": project_id, "service": "zhinen-pm", "contractVersion": "0.1", "database": {"pageCount": page_count, "pageSize": page_size, "bytes": page_count * page_size}, "outbox": {"queued": sum(row["status"] == "QUEUED" for row in sync_rows), "conflict": sum(row["status"] == "CONFLICT" for row in sync_rows), "failed": sum(row["status"] == "FAILED" for row in sync_rows)}, "eventOutbox": {"queued": sum(row["status"] == "QUEUED" for row in event_rows), "failed": sum(row["status"] == "FAILED" for row in event_rows), "published": sum(row["status"] == "PUBLISHED" for row in event_rows)}, "notifications": {"unread": unread}, "audit": {"count": audit_count, "writeFailures": 0}, "search": {"mode": "CANONICAL_QUERY", "freshness": "CURRENT"}, "backup": {"lastVerification": "ON_DEMAND", "status": "AVAILABLE"}, "deterministic": True}

    def sync_summary(self, project_id: str) -> dict[str, Any]:
        """Summarize offline replay safety without applying any queued change."""
        rows = self.list_sync_queue(project_id)
        status_counts = {status: sum(row["status"] == status for row in rows) for status in ("QUEUED", "APPLIED", "CONFLICT", "FAILED")}
        push_rows = [row for row in rows if row["direction"] == "PUSH_APPROVED"]
        missing_approval = [row["id"] for row in push_rows if not row["payload"].get("approvalId")]
        conflicts = [row["id"] for row in rows if row["status"] == "CONFLICT"]
        failed = [row["id"] for row in rows if row["status"] == "FAILED"]
        idempotency_keys = [row["idempotency_key"] for row in rows]
        unique_keys = len(idempotency_keys) == len(set(idempotency_keys))
        checks = {"idempotency": unique_keys, "pushApprovals": not missing_approval, "noConflicts": not conflicts, "noFailures": not failed}
        return {"projectId": project_id, "readyForReplay": all(checks.values()), "checks": checks, "statusCounts": status_counts, "queuedIds": [row["id"] for row in rows if row["status"] == "QUEUED"], "conflictIds": conflicts, "failedIds": failed, "missingApprovalIds": missing_approval, "deterministic": True, "generatedAt": now()}

    def acceptance_report(self, project_id: str) -> dict[str, Any]:
        stats = self.project_stats(project_id)
        readiness = self.backlog_readiness(project_id)
        entities = self.list_entities(project_id)
        releases = [x for x in entities if x["entity_type"] == "release"]
        evidence = [x for x in entities if x["entity_type"] == "evidence"]
        issues = [x for x in entities if x["entity_type"] == "issue"]
        gates = [self.release_gate(x["id"]) for x in releases]
        blockers = [x for x in readiness if x["blockedBy"]] + [{"releaseId": x["releaseId"], "missing": x["missing"]} for x in gates if not x["ready"]]
        backlog_items = self.list_backlog(project_id)
        software_ready = bool(stats["backlog"]) and all(item["status"] in {"VALIDATED", "RELEASED"} for item in backlog_items) and not any(x["blockedBy"] for x in readiness)
        data_ready = bool(backlog_items) and not any(item["placeholder"] for item in backlog_items)
        release_ready = bool(gates) and all(gate["ready"] for gate in gates)
        return {"projectId": project_id, "generatedAt": now(), "summary": {"workPackages": stats["backlog"], "readyWorkPackages": sum(1 for x in readiness if x["ready"]), "blockedWorkPackages": sum(1 for x in readiness if not x["ready"]), "validatedEvidence": sum(1 for x in evidence if x["status"] == "VALIDATED"), "machineObjects": len(self.list_machine_objects(project_id)), "artifacts": len(self.list_artifact_manifests(project_id)), "syncConflicts": sum(1 for x in self.list_sync_queue(project_id) if x["status"] == "CONFLICT"), "capabilitiesWithEvidence": sum(1 for x in self.capability_evidence(project_id) if x["ready"]), "openIssues": sum(1 for x in issues if x["status"] != "CLOSED"), "closedIssues": sum(1 for x in issues if x["status"] == "CLOSED"), "softwareReady": software_ready, "dataReady": data_ready, "releaseReady": release_ready}, "capabilityEvidence": self.capability_evidence(project_id), "releaseGates": gates, "blockers": blockers, "auditCount": len(self.list_audit(project_id))}

    def capability_evidence(self, project_id: str, capability_ids: list[str] | None = None) -> list[dict[str, Any]]:
        evidence = [x for x in self.list_entities(project_id, "evidence") if x["status"] == "VALIDATED"]
        by_capability: dict[str, list[str]] = {}
        for item in evidence:
            capability_id = item["payload"].get("capabilityId")
            if capability_id:
                by_capability.setdefault(capability_id, []).append(item["id"])
        ids = capability_ids or sorted(by_capability)
        return [{"capabilityId": capability_id, "validatedEvidence": by_capability.get(capability_id, []), "ready": bool(by_capability.get(capability_id))} for capability_id in ids]

    def list_audit(self, project_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit WHERE project_id = ? ORDER BY occurred_at DESC LIMIT ?", (project_id, limit))]

    def notify(self, *, notification_id: str, project_id: str, recipient_id: str, kind: str, message: str) -> dict[str, Any]:
        self.db.execute("INSERT OR IGNORE INTO notifications VALUES (?, ?, ?, ?, ?, 0, ?)", (notification_id, project_id, recipient_id, kind, message, now()))
        self.db.commit()
        return dict(self.db.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone())

    def notify_project_owner(self, *, project_id: str, kind: str, message: str, correlation_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        return self.notify(notification_id=f"NOTIFY-{correlation_id}", project_id=project_id, recipient_id=project["owner_id"], kind=kind, message=message)

    def list_notifications(self, recipient_id: str, project_id: str | None = None) -> list[dict[str, Any]]:
        if project_id:
            rows = self.db.execute("SELECT * FROM notifications WHERE recipient_id = ? AND project_id = ? ORDER BY created_at DESC", (recipient_id, project_id))
        else:
            rows = self.db.execute("SELECT * FROM notifications WHERE recipient_id = ? ORDER BY created_at DESC", (recipient_id,))
        return [dict(row) for row in rows]

    def mark_notification_read(self, notification_id: str) -> dict[str, Any]:
        self.db.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
        self.db.commit()
        row = self.db.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown notification: {notification_id}")
        return dict(row)

    def get_notification(self, notification_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown notification: {notification_id}")
        return dict(row)

    def backup(self, destination: str) -> str:
        target = sqlite3.connect(destination)
        try:
            self.db.backup(target)
        finally:
            target.close()
        return destination

    def verify_backup(self, destination: str, project_id: str) -> dict[str, Any]:
        target = sqlite3.connect(destination)
        target.row_factory = sqlite3.Row
        try:
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {row[0] for row in target.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            required_tables = {"projects", "users", "project_members", "entities", "audit", "sync_queue", "entity_links", "event_outbox"}
            source_counts = {name: self.db.execute(f"SELECT COUNT(*) FROM {name} WHERE project_id = ?", (project_id,)).fetchone()[0] for name in ("entities", "audit", "sync_queue", "entity_links", "event_outbox")}
            target_counts = {name: target.execute(f"SELECT COUNT(*) FROM {name} WHERE project_id = ?", (project_id,)).fetchone()[0] for name in ("entities", "audit", "sync_queue", "entity_links", "event_outbox") if name in tables}
            project_exists = bool(target.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone())
            revision_consistent = bool(target.execute("SELECT COUNT(*) FROM entities WHERE project_id = ? AND revision >= 1", (project_id,)).fetchone()[0] == target_counts.get("entities", -1))
            checks = {"integrity": integrity == "ok", "requiredTables": required_tables.issubset(tables), "project": project_exists, "coreCounts": source_counts == target_counts, "revisionConsistency": revision_consistent}
            return {"projectId": project_id, "backup": destination, "checks": checks, "ready": all(checks.values())}
        finally:
            target.close()

    def create_machine_object(self, *, object_id: str, project_id: str, tenant_id: str, object_type: str, name: str, owner_id: str, payload: dict[str, Any] | None = None, parent_id: str | None = None) -> dict[str, Any]:
        allowed = {"machine", "module", "device", "tag", "alarm", "recipe"}
        if object_type not in allowed:
            raise ValueError(f"unsupported machine object: {object_type}")
        if not self.db.execute("SELECT 1 FROM projects WHERE id = ? AND tenant_id = ?", (project_id, tenant_id)).fetchone():
            raise KeyError("project not found in tenant")
        if parent_id and not self.db.execute("SELECT 1 FROM machine_objects WHERE id = ? AND project_id = ?", (parent_id, project_id)).fetchone():
            raise KeyError("machine parent not found in project")
        data = payload or {}
        requirements = {"device": ("protocol",), "tag": ("dataType", "access"), "alarm": ("severity",), "recipe": ("version",)}
        missing = [field for field in requirements.get(object_type, ()) if not data.get(field)]
        if missing:
            raise ValueError(f"{object_type} missing fields: {', '.join(missing)}")
        if object_type == "tag" and data.get("access") not in {"READ_ONLY", "READ_WRITE"}:
            raise ValueError("tag access must be READ_ONLY or READ_WRITE")
        if object_type == "alarm" and data.get("severity") not in {"S0", "S1", "S2", "S3", "S4"}:
            raise ValueError("alarm severity must be S0-S4")
        timestamp = now()
        self.db.execute("INSERT INTO machine_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'DRAFT', ?, ?)", (object_id, project_id, tenant_id, object_type, parent_id, name, owner_id, json.dumps(payload or {}, ensure_ascii=False), timestamp, timestamp))
        self._audit(tenant_id, project_id, owner_id, "machine_object.create", object_id, "success", {"objectType": object_type, "parentId": parent_id})
        self._emit_event(tenant_id=tenant_id, project_id=project_id, message_type="pm.machine_object.created", actor_id=owner_id, payload={"objectId": object_id, "objectType": object_type, "parentId": parent_id, "status": "DRAFT", "revision": 1}, correlation_id=object_id, idempotency_key=f"machine_object.created:{object_id}:1")
        self.db.commit()
        return self.get_machine_object(object_id)

    def create_artifact_manifest(self, *, artifact_id: str, project_id: str, artifact_type: str, source_uri: str, content_hash: str, artifact_revision: str, toolchain_version: str, target_environment: str, sensitivity: str, owner_id: str) -> dict[str, Any]:
        if not content_hash or len(content_hash) < 8:
            raise ValueError("content_hash must be a verifiable digest")
        if sensitivity not in {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "EDGE_ONLY"}:
            raise ValueError("invalid artifact sensitivity")
        project = self.db.execute("SELECT tenant_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise KeyError(f"unknown project: {project_id}")
        timestamp = now()
        self.db.execute("INSERT INTO artifact_manifests (id, project_id, artifact_type, source_uri, content_hash, artifact_revision, toolchain_version, target_environment, sensitivity, owner_id, status, created_at, revision) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, 1)", (artifact_id, project_id, artifact_type, source_uri, content_hash, artifact_revision, toolchain_version, target_environment, sensitivity, owner_id, timestamp))
        self._audit(project["tenant_id"], project_id, owner_id, "artifact.create", artifact_id, "success", {"artifactType": artifact_type, "revision": artifact_revision})
        self._emit_event(tenant_id=project["tenant_id"], project_id=project_id, message_type="pm.artifact.created", actor_id=owner_id, payload={"artifactId": artifact_id, "artifactType": artifact_type, "status": "DRAFT", "revision": 1}, correlation_id=artifact_id, idempotency_key=f"artifact.created:{artifact_id}:1")
        self.db.commit()
        return self.get_artifact_manifest(artifact_id)

    def get_artifact_manifest(self, artifact_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM artifact_manifests WHERE id = ?", (artifact_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown artifact: {artifact_id}")
        return dict(row)

    def transition_artifact(self, *, artifact_id: str, target: str, actor_id: str, expected_revision: int | None = None) -> dict[str, Any]:
        artifact = self.get_artifact_manifest(artifact_id)
        if artifact["status"] == target:
            return artifact
        expected_revision = artifact["revision"] if expected_revision is None else expected_revision
        if artifact["revision"] != expected_revision:
            raise RuntimeError("PM-CONFLICT-001: artifact revision conflict")
        assert_transition("artifact", artifact["status"], target)
        cursor = self.db.execute("UPDATE artifact_manifests SET status = ?, revision = revision + 1 WHERE id = ? AND status = ? AND revision = ?", (target, artifact_id, artifact["status"], expected_revision))
        if cursor.rowcount != 1:
            raise RuntimeError("PM-CONFLICT-001: artifact revision conflict")
        project = self.db.execute("SELECT tenant_id FROM projects WHERE id = ?", (artifact["project_id"],)).fetchone()
        self._audit(project["tenant_id"] if project else "", artifact["project_id"], actor_id, "artifact.transition", artifact_id, "success", {"from": artifact["status"], "to": target})
        if project:
            self._emit_event(tenant_id=project["tenant_id"], project_id=artifact["project_id"], message_type="pm.artifact.transitioned", actor_id=actor_id, payload={"artifactId": artifact_id, "from": artifact["status"], "to": target, "revision": expected_revision + 1}, correlation_id=artifact_id, idempotency_key=f"artifact.transitioned:{artifact_id}:{expected_revision + 1}")
        self.db.commit()
        return self.get_artifact_manifest(artifact_id)

    def list_artifact_manifests(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM artifact_manifests WHERE project_id = ? ORDER BY created_at", (project_id,))]

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

    def create_machine_commit(self, *, commit_id: str, project_id: str, tenant_id: str, machine_snapshot_id: str, artifact_ids: list[str], branch: str, parent_commit_id: str | None, rollback_commit_id: str | None, actor_id: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(machine_snapshot_id)
        if snapshot["project_id"] != project_id:
            raise ValueError("machine snapshot must belong to project")
        if not artifact_ids:
            raise ValueError("machine commit requires artifacts")
        artifacts = [self.get_artifact_manifest(artifact_id) for artifact_id in artifact_ids]
        if any(artifact["project_id"] != project_id for artifact in artifacts):
            raise ValueError("machine commit artifacts must belong to project")
        if any(artifact["status"] not in {"TESTED", "APPROVED", "ARCHIVED"} for artifact in artifacts):
            raise ValueError("machine commit requires tested artifacts")
        components = [{"id": artifact["id"], "revision": artifact["artifact_revision"], "hash": artifact["content_hash"]} for artifact in artifacts]
        canonical = json.dumps({"snapshot": machine_snapshot_id, "branch": branch, "parent": parent_commit_id, "components": components}, sort_keys=True, separators=(",", ":"))
        commit_hash = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        commit = self.create_entity(entity_id=commit_id, entity_type="machine_commit", project_id=project_id, tenant_id=tenant_id, title=f"Machine Commit {commit_id}", owner_id=actor_id, payload={"machineSnapshotId": machine_snapshot_id, "artifactIds": artifact_ids, "components": components, "branch": branch, "parentCommitId": parent_commit_id, "rollbackCommitId": rollback_commit_id, "commitHash": commit_hash})
        commit = self.transition(entity_id=commit_id, target="BUILT", actor_id=actor_id, expected_revision=commit["revision"])
        return commit

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM machine_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown snapshot: {snapshot_id}")
        result = dict(row); result["payload"] = json.loads(result["payload"]); return result

    def list_snapshots(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT id, project_id, machine_id, revision, created_by, created_at FROM machine_snapshots WHERE project_id = ? ORDER BY created_at DESC", (project_id,))]

    def backlog_readiness(self, project_id: str) -> list[dict[str, Any]]:
        items = self.list_backlog(project_id)
        status = {item["id"]: item["status"] for item in items}
        ready_states = {"VALIDATED", "RELEASED"}
        result = []
        for item in items:
            missing = [dependency for dependency in item["dependencies"] if status.get(dependency) not in ready_states]
            contract_missing = []
            for field in ("owner_id", "target_release", "design_goal", "test_plan", "rollback_plan"):
                if not item.get(field):
                    contract_missing.append(field)
            if not item.get("acceptance_criteria"):
                contract_missing.append("acceptance_criteria")
            blockers = missing + ["contract:" + field for field in contract_missing]
            result.append({"id": item["id"], "status": item["status"], "placeholder": item["placeholder"], "ready": not blockers and item["status"] not in {"DEFERRED", "BLOCKED", "FAILED"}, "blockedBy": blockers, "contractReady": not contract_missing, "contractMissing": contract_missing})
        return result

    def update_machine_object(self, *, object_id: str, name: str | None, payload: dict[str, Any] | None, expected_revision: int, actor_id: str = "system") -> dict[str, Any]:
        current = self.get_machine_object(object_id)
        if current["revision"] != expected_revision:
            raise RuntimeError("PM-CONFLICT-001: machine object revision conflict")
        self.db.execute("UPDATE machine_objects SET name = ?, payload = ?, revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?", (name or current["name"], json.dumps(payload if payload is not None else current["payload"], ensure_ascii=False), now(), object_id, expected_revision))
        self._audit(current["tenant_id"], current["project_id"], actor_id, "machine_object.revision", object_id, "success", {"revision": expected_revision + 1})
        self._emit_event(tenant_id=current["tenant_id"], project_id=current["project_id"], message_type="pm.machine_object.revised", actor_id=actor_id, payload={"objectId": object_id, "objectType": current["object_type"], "revision": expected_revision + 1}, correlation_id=object_id, idempotency_key=f"machine_object.revised:{object_id}:{expected_revision + 1}")
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
        artifact_ids = release["payload"].get("artifactIds", [])
        artifacts = [self.get_artifact_manifest(x) for x in artifact_ids]
        untested_artifacts = [x["id"] for x in artifacts if x["status"] not in {"TESTED", "APPROVED", "ARCHIVED"}]
        approval = bool(release["payload"].get("approvalId"))
        signature = bool(release["payload"].get("signature"))
        sbom = bool(release["payload"].get("sbom"))
        rollback_revision = bool(release["payload"].get("rollbackRevision"))
        bindings = (("source revision", "sourceRevision"), ("Machine Project revision", "machineProjectRevision"), ("Schema version", "schemaVersion"), ("API version", "apiVersion"), ("Event version", "eventVersion"), ("known issues", "knownIssues"), ("target environment", "targetEnvironment"))
        missing_bindings = [label for label, field in bindings if field not in release["payload"] or release["payload"][field] in (None, "")]
        missing = (["validated evidence"] if not passed else []) + (["human approval"] if not approval else []) + ([f"tested artifacts: {', '.join(untested_artifacts)}"] if untested_artifacts else []) + (["signature"] if not signature else []) + (["SBOM"] if not sbom else []) + (["rollback revision"] if not rollback_revision else []) + missing_bindings
        return {"releaseId": release_id, "ready": not missing, "validatedEvidence": [x["id"] for x in passed], "artifacts": [x["id"] for x in artifacts], "approval": approval, "signature": signature, "sbom": sbom, "rollbackRevision": release["payload"].get("rollbackRevision"), "missing": missing}

    def release_preflight(self, release_id: str) -> dict[str, Any]:
        """Check release composition consistency before a human release decision."""
        release = self.get_entity(release_id)
        if release["entity_type"] != "release":
            raise ValueError("preflight target must be release")
        payload = release["payload"]
        errors: list[str] = []
        artifact_ids = payload.get("artifactIds", [])
        artifacts = []
        for artifact_id in artifact_ids:
            try:
                artifact = self.get_artifact_manifest(artifact_id)
            except KeyError:
                errors.append("artifact_missing:" + str(artifact_id))
                continue
            artifacts.append(artifact)
            if artifact["project_id"] != release["project_id"]:
                errors.append("artifact_project_mismatch:" + artifact_id)
            if artifact["status"] not in {"TESTED", "APPROVED", "ARCHIVED"}:
                errors.append("artifact_not_tested:" + artifact_id)
        if not artifact_ids:
            errors.append("artifacts_required")
        if payload.get("machineCommitId"):
            try:
                commit = self.get_entity(payload["machineCommitId"])
                if commit["project_id"] != release["project_id"] or commit["entity_type"] != "machine_commit":
                    errors.append("machine_commit_project_or_type_invalid")
                elif set(commit["payload"].get("artifactIds", [])) != set(artifact_ids):
                    errors.append("machine_commit_artifacts_mismatch")
            except KeyError:
                errors.append("machine_commit_missing:" + str(payload["machineCommitId"]))
        if payload.get("parameterSnapshotId"):
            try:
                snapshot = self.get_entity(payload["parameterSnapshotId"])
                if snapshot["project_id"] != release["project_id"] or snapshot["entity_type"] != "parameter_snapshot" or snapshot["status"] not in {"APPROVED", "APPLIED"}:
                    errors.append("parameter_snapshot_not_approved")
            except KeyError:
                errors.append("parameter_snapshot_missing:" + str(payload["parameterSnapshotId"]))
        if payload.get("sbomFormat") and payload["sbomFormat"] != "zhinen-sbom-v1":
            errors.append("sbom_format_invalid")
        integrity = self.integrity_audit(release["project_id"])
        if not integrity["ready"]:
            errors.append("project_integrity_failed")
        try:
            gate = self.release_gate(release_id)
        except KeyError:
            gate = {"releaseId": release_id, "ready": False, "missing": ["artifact reference unresolved"], "validatedEvidence": [], "artifacts": []}
        checks = {"artifacts": bool(artifacts) and not any(item.startswith("artifact_") for item in errors), "artifactHashes": all(str(item["content_hash"]).startswith("sha256:") for item in artifacts), "gate": gate["ready"], "machineCommit": not any(item.startswith("machine_commit_") for item in errors), "parameterSnapshot": not any(item.startswith("parameter_snapshot_") for item in errors), "integrity": integrity["ready"]}
        if not checks["artifactHashes"]:
            errors.append("artifact_hash_invalid")
        return {"releaseId": release_id, "ready": not errors and gate["ready"], "checks": checks, "errors": sorted(set(errors)), "gate": gate, "integrity": integrity, "artifactIds": artifact_ids, "artifactRevisions": [{"id": item["id"], "revision": item["artifact_revision"], "hash": item["content_hash"]} for item in artifacts]}

    def compose_release(self, *, release_id: str, artifact_ids: list[str], rollback_revision: str, actor_id: str) -> dict[str, Any]:
        release = self.get_entity(release_id)
        if release["entity_type"] != "release":
            raise ValueError("release composition target must be release")
        if not artifact_ids:
            raise ValueError("release requires at least one artifact")
        artifacts = [self.get_artifact_manifest(artifact_id) for artifact_id in artifact_ids]
        if any(artifact["project_id"] != release["project_id"] for artifact in artifacts):
            raise ValueError("release artifacts must belong to the same project")
        untested = [artifact["id"] for artifact in artifacts if artifact["status"] not in {"TESTED", "APPROVED", "ARCHIVED"}]
        if untested:
            raise ValueError(f"release artifacts are not tested: {', '.join(untested)}")
        components = [{"id": artifact["id"], "type": artifact["artifact_type"], "revision": artifact["artifact_revision"], "hash": artifact["content_hash"], "toolchain": artifact["toolchain_version"]} for artifact in artifacts]
        sbom_payload = json.dumps({"format": "zhinen-sbom-v1", "releaseId": release_id, "components": components}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sbom = f"sha256:{hashlib.sha256(sbom_payload.encode()).hexdigest()}"
        payload = {**release["payload"], "artifactIds": artifact_ids, "sbom": sbom, "sbomFormat": "zhinen-sbom-v1", "components": components, "rollbackRevision": rollback_revision}
        updated = self.update_entity_payload(entity_id=release_id, payload=payload, actor_id=actor_id, expected_revision=release["revision"])
        return {"release": updated, "sbom": sbom, "components": components, "gate": self.release_gate(release_id)}

    def execute_test_case(self, *, project_id: str, tenant_id: str, test_case_id: str, run_id: str, evidence_id: str, actor_id: str, passed: bool, release_id: str | None = None, issue_id: str | None = None, environment: str = "SIMULATION") -> dict[str, Any]:
        case = self.get_entity(test_case_id)
        if case["project_id"] != project_id or case["entity_type"] != "test_case":
            raise KeyError("test case not found in project")
        required_definition = ("steps", "inputs", "expected", "thresholds")
        if any(not case["payload"].get(field) for field in required_definition):
            raise ValueError("PM-TEST-001: test case execution needs steps, inputs, expected results and thresholds")
        run_payload = {"testCaseId": test_case_id, "testCaseRevision": case["revision"], "environment": environment, "executedBy": actor_id, "result": "PASSED" if passed else "FAILED"}
        run = self.create_entity(entity_id=run_id, entity_type="test_run", project_id=project_id, tenant_id=tenant_id, title=f"Run: {case['title']}", owner_id=actor_id, payload=run_payload)
        self.transition(entity_id=run_id, target="RUNNING", actor_id=actor_id, expected_revision=1)
        final = self.transition(entity_id=run_id, target="PASSED" if passed else "FAILED", actor_id=actor_id, expected_revision=2)
        evidence = self.create_entity(entity_id=evidence_id, entity_type="evidence", project_id=project_id, tenant_id=tenant_id, title=f"Evidence: {case['title']}", owner_id=actor_id, payload={"testRunId": run_id, "testCaseId": test_case_id, "testCaseRevision": case["revision"], "environment": environment, "executedBy": actor_id, "source": "test-case-execution", "result": "PASSED" if passed else "FAILED"})
        self.link_entities(project_id=project_id, from_id=test_case_id, to_id=evidence_id, link_type="produces", actor_id=actor_id)
        issue = None
        if passed:
            evidence = self.transition(entity_id=evidence_id, target="VALIDATED", actor_id=actor_id, expected_revision=1)
            if release_id:
                self.link_entities(project_id=project_id, from_id=release_id, to_id=evidence_id, link_type="requires", actor_id=actor_id)
        else:
            issue = self.create_entity(entity_id=issue_id or f"ISSUE-{run_id}", entity_type="issue", project_id=project_id, tenant_id=tenant_id, title=f"Test case failed: {case['title']}", owner_id=actor_id, payload={"sourceTestRunId": run_id, "evidenceId": evidence_id, "evidenceLinks": [evidence_id], "testCaseId": test_case_id})
            self.link_entities(project_id=project_id, from_id=issue["id"], to_id=evidence_id, link_type="diagnosed_by", actor_id=actor_id)
            self.notify_project_owner(project_id=project_id, kind="test_failed", message=f"Test case failed: {issue['id']}", correlation_id=run_id)
        return {"testRun": final, "evidence": evidence, "issue": issue}

    def execute_test_plan(self, *, project_id: str, tenant_id: str, test_plan_id: str, actor_id: str, run_prefix: str, evidence_prefix: str, passed_by_case: dict[str, bool] | None = None, release_id: str | None = None, environment: str = "SIMULATION") -> dict[str, Any]:
        plan = self.get_entity(test_plan_id)
        if plan["project_id"] != project_id or plan["entity_type"] != "test_plan":
            raise KeyError("test plan not found in project")
        test_case_ids = plan["payload"].get("testCaseIds", [])
        if not test_case_ids:
            raise ValueError("test plan requires testCaseIds")
        if plan["status"] == "DRAFT":
            plan = self.transition(entity_id=test_plan_id, target="READY", actor_id=actor_id, expected_revision=plan["revision"])
        if plan["status"] == "READY":
            plan = self.transition(entity_id=test_plan_id, target="RUNNING", actor_id=actor_id, expected_revision=plan["revision"])
        if plan["status"] != "RUNNING":
            raise ValueError(f"test plan is not executable: {plan['status']}")
        results = []
        passed_by_case = passed_by_case or {}
        for index, test_case_id in enumerate(test_case_ids, start=1):
            result = self.execute_test_case(project_id=project_id, tenant_id=tenant_id, test_case_id=test_case_id, run_id=f"{run_prefix}-{index}", evidence_id=f"{evidence_prefix}-{index}", actor_id=actor_id, passed=bool(passed_by_case.get(test_case_id, True)), release_id=release_id, environment=environment)
            results.append(result)
        all_passed = all(item["testRun"]["status"] == "PASSED" for item in results)
        plan = self.transition(entity_id=test_plan_id, target="COMPLETED" if all_passed else "FAILED", actor_id=actor_id, expected_revision=plan["revision"])
        return {"testPlan": plan, "results": results, "summary": {"total": len(results), "passed": sum(item["testRun"]["status"] == "PASSED" for item in results), "failed": sum(item["testRun"]["status"] == "FAILED" for item in results)}}

    def link_entities(self, *, project_id: str, from_id: str, to_id: str, link_type: str, actor_id: str = "system") -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM entities WHERE id = ? AND project_id = ?", (from_id, project_id)).fetchone() or not self.db.execute("SELECT 1 FROM entities WHERE id = ? AND project_id = ?", (to_id, project_id)).fetchone():
            raise KeyError("entity link target not found in project")
        self.db.execute("INSERT OR IGNORE INTO entity_links VALUES (?, ?, ?, ?, ?)", (project_id, from_id, to_id, link_type, now()))
        project = self.db.execute("SELECT tenant_id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if project:
            self._emit_event(tenant_id=project["tenant_id"], project_id=project_id, message_type="pm.entity.linked", actor_id=actor_id, payload={"fromId": from_id, "toId": to_id, "linkType": link_type}, correlation_id=f"{from_id}:{to_id}:{link_type}", idempotency_key=f"entity.linked:{project_id}:{from_id}:{to_id}:{link_type}")
            self._audit(project["tenant_id"], project_id, actor_id, "entity.link", f"{from_id}:{to_id}", "success", {"linkType": link_type})
        self.db.commit()
        return {"project_id": project_id, "from_id": from_id, "to_id": to_id, "link_type": link_type}

    def list_links(self, project_id: str, entity_id: str | None = None) -> list[dict[str, Any]]:
        if entity_id:
            rows = self.db.execute("SELECT * FROM entity_links WHERE project_id = ? AND (from_id = ? OR to_id = ?) ORDER BY created_at", (project_id, entity_id, entity_id))
        else:
            rows = self.db.execute("SELECT * FROM entity_links WHERE project_id = ? ORDER BY created_at", (project_id,))
        return [dict(row) for row in rows]

    def traceability_graph(self, project_id: str) -> dict[str, Any]:
        entities = self.list_entities(project_id)
        by_id = {item["id"]: item for item in entities}
        nodes = [{"id": item["id"], "type": item["entity_type"], "status": item["status"], "ownerId": item["owner_id"], "revision": item["revision"]} for item in entities]
        edges = [{"from": item["from_id"], "to": item["to_id"], "type": item["link_type"], "source": "entity_links"} for item in self.list_links(project_id)]
        unresolved = []
        reference_fields = {"evidenceLinks": "evidence", "testIds": "tested_by", "regressionTestIds": "regression_test", "testCaseIds": "contains_test", "artifactIds": "contains_artifact", "releaseId": "release", "sourceTestRunId": "source_run", "evidenceId": "evidence", "parentCommitId": "parent_commit", "rollbackCommitId": "rollback_commit"}
        seen = {(edge["from"], edge["to"], edge["type"]) for edge in edges}
        for item in entities:
            for field, edge_type in reference_fields.items():
                references = item["payload"].get(field, [])
                if isinstance(references, str):
                    references = [references]
                if not isinstance(references, list):
                    continue
                for target_id in references:
                    if target_id in by_id:
                        key = (item["id"], target_id, edge_type)
                        if key not in seen:
                            edges.append({"from": item["id"], "to": target_id, "type": edge_type, "source": "payload"}); seen.add(key)
                    else:
                        unresolved.append({"from": item["id"], "field": field, "reference": target_id})
        return {"projectId": project_id, "nodes": nodes, "edges": edges, "unresolvedReferences": unresolved, "freshness": "CURRENT", "generatedAt": now()}

    def integrity_audit(self, project_id: str) -> dict[str, Any]:
        """Run a read-only consistency audit across the project control-plane graph."""
        entities = self.list_entities(project_id)
        entity_ids = {item["id"] for item in entities}
        errors: list[dict[str, Any]] = []
        for item in entities:
            if not item["id"] or item["revision"] < 1:
                errors.append({"code": "entity_revision_invalid", "id": item["id"]})
            if not item["owner_id"]:
                errors.append({"code": "entity_owner_missing", "id": item["id"]})
        links = self.list_links(project_id)
        for link in links:
            if link["from_id"] not in entity_ids or link["to_id"] not in entity_ids:
                errors.append({"code": "link_target_missing", "from": link["from_id"], "to": link["to_id"]})
        graph = self.traceability_graph(project_id)
        artifact_ids = {item["id"] for item in self.list_artifact_manifests(project_id)}
        for reference in graph["unresolvedReferences"]:
            if reference["field"] == "artifactIds" and reference["reference"] in artifact_ids:
                continue
            errors.append({"code": "reference_unresolved", **reference})
        artifacts = self.list_artifact_manifests(project_id)
        for artifact in artifacts:
            if not str(artifact["content_hash"]).startswith("sha256:"):
                errors.append({"code": "artifact_hash_invalid", "id": artifact["id"]})
        checks = {
            "entityRevisions": not any(item["code"] == "entity_revision_invalid" for item in errors),
            "entityOwners": not any(item["code"] == "entity_owner_missing" for item in errors),
            "linkTargets": not any(item["code"] == "link_target_missing" for item in errors),
            "references": not any(item["code"] == "reference_unresolved" for item in errors),
            "artifactHashes": not any(item["code"] == "artifact_hash_invalid" for item in errors),
        }
        return {"projectId": project_id, "ready": all(checks.values()), "checks": checks, "errors": errors, "counts": {"entities": len(entities), "links": len(links), "artifacts": len(artifacts)}, "deterministic": True, "generatedAt": now()}

    def search(self, project_id: str, query: str) -> list[dict[str, Any]]:
        needle = f"%{query}%"
        rows = self.db.execute("SELECT id, entity_type, title, status, owner_id, updated_at FROM entities WHERE project_id = ? AND (id LIKE ? OR title LIKE ?) ORDER BY updated_at DESC", (project_id, needle, needle)).fetchall()
        return [dict(row) for row in rows]

    def transition_sync(self, sync_id: str, target: str, reason: str = "", actor_id: str = "system") -> dict[str, Any]:
        allowed = {"QUEUED": {"APPLIED", "CONFLICT", "FAILED"}, "CONFLICT": {"QUEUED", "FAILED"}, "FAILED": {"QUEUED"}, "APPLIED": set()}
        row = self.db.execute("SELECT * FROM sync_queue WHERE id = ?", (sync_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown sync: {sync_id}")
        if target not in allowed.get(row["status"], set()):
            raise ValueError(f"PM-SYNC-002: invalid transition {row['status']}->{target}")
        if row["status"] == "CONFLICT" and not reason.strip():
            raise ValueError("PM-SYNC-003: conflict resolution requires a reason")
        self.db.execute("UPDATE sync_queue SET status = ?, reason = ?, updated_at = ? WHERE id = ?", (target, reason, now(), sync_id))
        self._audit(row["tenant_id"], row["project_id"], actor_id, "sync.transition", sync_id, "success", {"from": row["status"], "to": target, "reason": reason})
        self._emit_event(tenant_id=row["tenant_id"], project_id=row["project_id"], message_type="pm.sync.transitioned", actor_id=actor_id, payload={"syncId": sync_id, "from": row["status"], "to": target, "reason": reason}, correlation_id=sync_id, idempotency_key=f"sync.transitioned:{sync_id}:{target}:{row['updated_at']}")
        self.db.commit()
        if target in {"CONFLICT", "FAILED"}:
            self.notify_project_owner(project_id=row["project_id"], kind="sync_conflict" if target == "CONFLICT" else "sync_failed", message=f"Sync {sync_id} entered {target}: {reason or 'no reason'}", correlation_id=sync_id)
        result = dict(self.db.execute("SELECT * FROM sync_queue WHERE id = ?", (sync_id,)).fetchone()); result["payload"] = json.loads(result["payload"]); return result

    def get_sync(self, sync_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM sync_queue WHERE id = ?", (sync_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown sync: {sync_id}")
        result = dict(row); result["payload"] = json.loads(result["payload"]); return result

    def create_entity(self, *, entity_id: str, entity_type: str, project_id: str, tenant_id: str, title: str, owner_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.db.execute("SELECT 1 FROM projects WHERE id = ? AND tenant_id = ?", (project_id, tenant_id)).fetchone():
            raise KeyError("project not found in tenant")
        status = {"requirement": "DRAFT", "design_goal": "DRAFT", "work_item": "PLANNED", "issue": "OPEN", "adr": "PROPOSED", "test_case": "DRAFT", "knowledge": "DRAFT", "release": "DRAFT", "test_plan": "DRAFT", "test_run": "QUEUED", "evidence": "DRAFT", "tool_validation": "DRAFT", "artifact": "DRAFT", "parameter_snapshot": "DRAFT", "maintenance": "OPEN", "deployment": "REQUESTED", "machine_commit": "DRAFT", "ai_suggestion": "DRAFT"}.get(entity_type)
        if entity_type == "review":
            status = "REQUESTED"
        if status is None:
            raise ValueError(f"unsupported PM-0 entity: {entity_type}")
        entity_payload = payload or {}
        if entity_type == "issue" and entity_payload.get("severity") and entity_payload["severity"] not in {"S0", "S1", "S2", "S3", "S4"}:
            raise ValueError("issue severity must be S0-S4")
        timestamp = now()
        self.db.execute("INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)", (entity_id, project_id, tenant_id, entity_type, title, status, owner_id, json.dumps(entity_payload, ensure_ascii=False), timestamp, timestamp))
        self._audit(tenant_id, project_id, owner_id, f"{entity_type}.create", entity_id, "success", {})
        event_name = {"issue": "opened", "test_run": "queued", "deployment": "requested", "review": "requested"}.get(entity_type, "created")
        self._emit_event(tenant_id=tenant_id, project_id=project_id, message_type=f"pm.{entity_type}.{event_name}", actor_id=owner_id, payload={"entityId": entity_id, "entityType": entity_type, "status": status, "revision": 1}, correlation_id=entity_id, idempotency_key=f"{entity_type}.{event_name}:{entity_id}:1")
        self.db.commit()
        if entity_type == "issue" and entity_payload.get("severity") in {"S0", "S1"}:
            self.notify_project_owner(project_id=project_id, kind="issue_escalation", message=f"{entity_payload['severity']} issue requires escalation: {entity_id}", correlation_id=f"ISSUE-ESCALATION-{entity_id}")
        return self.get_entity(entity_id)

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown entity: {entity_id}")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def update_entity_payload(self, *, entity_id: str, payload: dict[str, Any], actor_id: str, expected_revision: int) -> dict[str, Any]:
        entity = self.get_entity(entity_id)
        if entity["revision"] != expected_revision:
            raise RuntimeError("PM-CONFLICT-001: entity revision conflict")
        self.db.execute("UPDATE entities SET payload = ?, revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?", (json.dumps(payload, ensure_ascii=False), now(), entity_id, expected_revision))
        self._audit(entity["tenant_id"], entity["project_id"], actor_id, f"{entity['entity_type']}.payload.update", entity_id, "success", {})
        self._emit_event(tenant_id=entity["tenant_id"], project_id=entity["project_id"], message_type=f"pm.{entity['entity_type']}.revised", actor_id=actor_id, payload={"entityId": entity_id, "entityType": entity["entity_type"], "revision": expected_revision + 1}, correlation_id=entity_id, idempotency_key=f"{entity['entity_type']}.revised:{entity_id}:{expected_revision + 1}")
        self.db.commit()
        return self.get_entity(entity_id)

    def apply_parameter_snapshot(self, *, snapshot_id: str, sync_id: str, approval_id: str, actor_id: str) -> dict[str, Any]:
        snapshot = self.get_entity(snapshot_id)
        if snapshot["entity_type"] != "parameter_snapshot" or snapshot["status"] != "APPROVED":
            raise ValueError("parameter snapshot must be APPROVED before apply")
        sync = self.enqueue_sync(sync_id=sync_id, project_id=snapshot["project_id"], tenant_id=snapshot["tenant_id"], direction="PUSH_APPROVED", object_type="parameter_snapshot", object_id=snapshot_id, idempotency_key=f"apply:{snapshot_id}:{approval_id}", payload={"snapshotId": snapshot_id, "approvalId": approval_id, "parameters": snapshot["payload"]}, actor_id=actor_id)
        applied = self.transition(entity_id=snapshot_id, target="APPLIED", actor_id=actor_id, expected_revision=snapshot["revision"], allow_parameter_apply=True)
        return {"snapshot": applied, "sync": sync}

    def apply_ai_suggestion(self, *, suggestion_id: str, target_entity_id: str, target_expected_revision: int, patch: dict[str, Any], approval_id: str, test_evidence_id: str, actor_id: str) -> dict[str, Any]:
        """Apply an AI-produced patch only after an authorized human approval."""
        suggestion = self.get_entity(suggestion_id)
        if suggestion["entity_type"] != "ai_suggestion":
            raise ValueError("AI apply target must be an ai_suggestion")
        if suggestion["payload"].get("applied"):
            raise ValueError("AI suggestion has already been applied")
        if not approval_id:
            raise PermissionError("PM-AI-APPLY-001: human approvalId is required")
        evidence = self.get_entity(test_evidence_id)
        if evidence["project_id"] != suggestion["project_id"] or evidence["entity_type"] != "evidence" or evidence["status"] != "VALIDATED":
            raise ValueError("PM-AI-APPLY-007: Apply requires same-project VALIDATED test evidence")
        actor = self.get_actor(actor_id, suggestion["tenant_id"])
        if actor["role"] == "ai":
            raise PermissionError("PM-AI-APPLY-002: AI actor cannot apply suggestions")
        target = self.get_entity(target_entity_id)
        if target["project_id"] != suggestion["project_id"]:
            raise ValueError("PM-AI-APPLY-003: target must belong to the suggestion project")
        if target["entity_type"] in {"release", "deployment", "artifact", "machine_commit", "parameter_snapshot"}:
            raise PermissionError("PM-AI-APPLY-004: controlled release/deployment objects require their dedicated gate")
        if target["revision"] != target_expected_revision:
            raise RuntimeError("PM-CONFLICT-001: AI target revision conflict")
        if not isinstance(patch, dict) or not patch:
            raise ValueError("PM-AI-APPLY-005: non-empty patch is required")
        forbidden = {"force", "force_io", "deploy", "deployment", "approval", "approvalid", "safety_override", "direct_deploy"}
        def contains_forbidden(value: Any) -> bool:
            if isinstance(value, dict):
                return any(str(key).lower().replace("_", "") in {item.replace("_", "") for item in forbidden} or contains_forbidden(item) for key, item in value.items())
            if isinstance(value, list):
                return any(contains_forbidden(item) for item in value)
            return False
        if contains_forbidden(patch):
            raise PermissionError("PM-AI-APPLY-006: patch contains a forbidden control action")
        updated_target = self.update_entity_payload(entity_id=target_entity_id, payload={**target["payload"], **patch}, actor_id=actor_id, expected_revision=target_expected_revision)
        suggestion_payload = {**suggestion["payload"], "applied": True, "appliedBy": actor_id, "approvalId": approval_id, "testEvidenceId": test_evidence_id, "targetEntityId": target_entity_id, "targetRevision": target_expected_revision, "patch": patch}
        updated_suggestion = self.update_entity_payload(entity_id=suggestion_id, payload=suggestion_payload, actor_id=actor_id, expected_revision=suggestion["revision"])
        self.link_entities(project_id=suggestion["project_id"], from_id=suggestion_id, to_id=target_entity_id, link_type="applied_to", actor_id=actor_id)
        return {"suggestion": updated_suggestion, "target": updated_target, "approvalId": approval_id, "applied": True}

    def deployment_preflight(self, deployment_id: str) -> dict[str, Any]:
        """Check deployment inputs and release readiness before any state transition."""
        deployment = self.get_entity(deployment_id)
        if deployment["entity_type"] != "deployment":
            raise ValueError("deployment preflight target must be deployment")
        payload = deployment["payload"]
        required = ("releaseId", "targetMachineId", "environment", "approvalId", "rollbackRevision", "observationWindow")
        missing = [field for field in required if not payload.get(field)]
        release = None
        release_errors: list[str] = []
        if payload.get("releaseId"):
            try:
                release = self.get_entity(payload["releaseId"])
                if release["project_id"] != deployment["project_id"] or release["entity_type"] != "release":
                    release_errors.append("release_project_or_type_invalid")
                else:
                    release_check = self.release_preflight(release["id"])
                    if not release_check["ready"]:
                        release_errors.extend("release:" + error for error in release_check["errors"] or release_check["gate"].get("missing", []))
            except KeyError:
                release_errors.append("release_missing")
        checks = {"inputs": not missing, "release": release is not None and not release_errors, "signature": bool(payload.get("signature")), "healthCheck": bool(payload.get("healthCheck")), "observation": bool(payload.get("observationWindow"))}
        authorization_ready = checks["inputs"] and checks["release"]
        staging_ready = authorization_ready and checks["signature"]
        observation_ready = staging_ready and checks["healthCheck"] and checks["observation"]
        return {"deploymentId": deployment_id, "readyForAuthorization": authorization_ready, "readyForStaging": staging_ready, "readyForObservation": observation_ready, "checks": checks, "missing": missing + release_errors, "currentStatus": deployment["status"], "releaseId": payload.get("releaseId"), "targetMachineId": payload.get("targetMachineId"), "deterministic": True, "generatedAt": now()}

    def list_entities(self, project_id: str, entity_type: str | None = None) -> list[dict[str, Any]]:
        if entity_type:
            rows = self.db.execute("SELECT * FROM entities WHERE project_id = ? AND entity_type = ? ORDER BY updated_at DESC", (project_id, entity_type)).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM entities WHERE project_id = ? ORDER BY updated_at DESC", (project_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row); item["payload"] = json.loads(item["payload"]); result.append(item)
        return result

    def transition(self, *, entity_id: str, target: str, actor_id: str, expected_revision: int, allow_parameter_apply: bool = False) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown entity: {entity_id}")
        if row["revision"] != expected_revision:
            raise RuntimeError("PM-CONFLICT-001: revision conflict")
        if row["entity_type"] == "parameter_snapshot" and target == "APPLIED" and not allow_parameter_apply:
            raise ValueError("PM-PARAM-002: use approved parameter apply endpoint")
        payload = json.loads(row["payload"])
        if row["entity_type"] == "requirement" and target == "READY":
            required = ("description", "priority", "acceptanceCriteria", "nonGoals", "source", "traceLinks")
            if any(not payload.get(field) for field in required):
                raise ValueError("PM-REQ-001: requirement ready needs description, priority, acceptance criteria, non-goals, source and trace links")
        if row["entity_type"] == "design_goal" and target == "READY":
            required = ("purpose", "inputs", "outputs", "constraints", "metrics", "failureBehavior", "risk", "testPlanId", "acceptanceThresholds")
            if any(not payload.get(field) for field in required):
                raise ValueError("PM-DESIGN-001: design goal ready needs purpose, IO, constraints, metrics, failure behavior, risk, test plan and thresholds")
        if row["entity_type"] == "review" and target == "APPROVED":
            required = ("reviewerId", "reviewedRevision", "decision", "comments")
            if any(not payload.get(field) for field in required) or payload.get("decision") != "APPROVED":
                raise ValueError("PM-REVIEW-001: review approval needs reviewer, revision, APPROVED decision and comments")
            if payload.get("reviewerId") == row["owner_id"]:
                raise ValueError("PM-REVIEW-002: review owner cannot approve their own review")
        if row["entity_type"] == "release" and target == "RELEASED":
            gate = self.release_gate(entity_id)
            if not gate["ready"]:
                raise ValueError("PM-RELEASE-001: release gate is not satisfied")
        if row["entity_type"] == "work_item" and target == "DONE":
            if not payload.get("evidenceLinks"):
                raise ValueError("PM-QUALITY-001: work item needs evidenceLinks before DONE")
        if row["entity_type"] == "issue" and target == "CLOSED":
            required = ("rootCause", "fixVersion", "regressionTestIds", "closureCriteria")
            if any(not payload.get(field) for field in required):
                raise ValueError("PM-QUALITY-002: issue closure needs root cause, fix version, regression test and criteria")
            evidence_links = payload.get("evidenceLinks", [])
            if not evidence_links:
                raise ValueError("PM-QUALITY-003: issue closure needs evidenceLinks")
            for evidence_id in evidence_links:
                evidence_row = self.db.execute("SELECT project_id, entity_type, status FROM entities WHERE id = ?", (evidence_id,)).fetchone()
                if not evidence_row or evidence_row["project_id"] != row["project_id"] or evidence_row["entity_type"] != "evidence" or evidence_row["status"] != "VALIDATED":
                    raise ValueError("PM-QUALITY-003: issue closure needs validated project evidence")
        if row["entity_type"] == "knowledge" and target == "APPROVED":
            required = ("source", "applicableVersion", "validationStatus", "testIds", "expiryCondition")
            if any(not payload.get(field) for field in required) or payload.get("validationStatus") != "VALIDATED":
                raise ValueError("PM-KNOWLEDGE-001: knowledge approval needs source, version, validated status, tests and expiry condition")
        if row["entity_type"] == "maintenance" and target in {"COMPLETED", "CLOSED"}:
            required = ("machineId", "executorId", "releaseId", "result", "exceptions", "rollback")
            if any(field not in payload or (payload[field] is None) for field in required):
                raise ValueError("PM-MAINT-001: maintenance completion needs machine, executor, release, result, exceptions and rollback")
        if row["entity_type"] == "deployment":
            if target == "AUTHORIZED":
                required = ("releaseId", "targetMachineId", "environment", "approvalId", "rollbackRevision", "observationWindow")
                if any(not payload.get(field) for field in required):
                    raise ValueError("PM-DEPLOY-001: authorization needs release, target, environment, approval, rollback and observation window")
                release_row = self.db.execute("SELECT project_id, entity_type, status FROM entities WHERE id = ?", (payload["releaseId"],)).fetchone()
                if not release_row or release_row["project_id"] != row["project_id"] or release_row["entity_type"] != "release" or release_row["status"] not in {"APPROVED", "RELEASED"}:
                    raise ValueError("PM-DEPLOY-002: deployment requires approved project release")
                if not self.release_gate(payload["releaseId"])["ready"]:
                    raise ValueError("PM-DEPLOY-002: deployment requires release gate")
            if target == "STAGED" and not payload.get("signature"):
                raise ValueError("PM-DEPLOY-003: staged deployment requires signed package")
            if target == "OBSERVED" and not payload.get("healthCheck"):
                raise ValueError("PM-DEPLOY-004: observed deployment requires health check")
            if target == "CONFIRMED" and payload.get("observationResult") != "PASS":
                raise ValueError("PM-DEPLOY-005: confirmation requires passing observation")
            if target == "ROLLED_BACK" and not payload.get("rollbackReason"):
                raise ValueError("PM-DEPLOY-006: rollback requires reason")
        assert_transition(row["entity_type"], row["status"], target)
        timestamp = now()
        self.db.execute("UPDATE entities SET status = ?, revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?", (target, timestamp, entity_id, expected_revision))
        self._audit(row["tenant_id"], row["project_id"], actor_id, f"{row['entity_type']}.transition", entity_id, "success", {"from": row["status"], "to": target})
        event_name = {("requirement", "ACCEPTED"): "accepted", ("work_item", "DONE"): "completed", ("issue", "CLOSED"): "closed", ("test_run", "PASSED"): "passed", ("test_run", "FAILED"): "failed", ("release", "APPROVED"): "approved", ("deployment", "CONFIRMED"): "confirmed", ("knowledge", "APPROVED"): "approved"}.get((row["entity_type"], target), "transitioned")
        self._emit_event(tenant_id=row["tenant_id"], project_id=row["project_id"], message_type=f"pm.{row['entity_type']}.{event_name}", actor_id=actor_id, payload={"entityId": entity_id, "entityType": row["entity_type"], "from": row["status"], "to": target, "revision": expected_revision + 1}, correlation_id=entity_id, idempotency_key=f"{row['entity_type']}.{event_name}:{entity_id}:{expected_revision + 1}")
        self.db.commit()
        return self.get_entity(entity_id)

    def audit(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit WHERE project_id = ? ORDER BY occurred_at", (project_id,))]

    def record_ai_context_access(self, *, project_id: str, actor_id: str, object_ids: list[str], omitted_ids: list[str]) -> None:
        project = self.get_project(project_id)
        self._audit(project["tenant_id"], project_id, actor_id, "ai.context.read", project_id, "success", {"objectIds": object_ids, "omittedIds": omitted_ids})
        self.db.commit()

    def close(self) -> None:
        self.db.close()
