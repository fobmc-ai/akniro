"""Transport-neutral Project Service facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .envelope import make_message
from .outbox import Outbox
from .store import ProjectStore


class ServiceError(RuntimeError):
    pass


@dataclass
class ProjectService:
    store: ProjectStore
    audit: AuditLog
    outbox: Outbox

    def save_revision(self, project: dict[str, Any], *, actor: str, tenant_id: str, site_id: str, machine_id: str) -> str:
        message = make_message("command", "project.revision.save", {"revision": project.get("revision")}, actor=actor, tenant_id=tenant_id, site_id=site_id, machine_id=machine_id)
        try:
            path = self.store.save(project)
        except Exception as exc:
            self.audit.append(action="project.revision.save", actor=actor, target=str(project.get("projectId", "unknown")), outcome="failure", correlation_id=message.correlationId, details={"error": str(exc)})
            raise ServiceError(str(exc)) from exc
        self.audit.append(action="project.revision.save", actor=actor, target=project["projectId"], outcome="success", correlation_id=message.correlationId, details={"revision": project["revision"]})
        self.outbox.append(make_message("event", "project.revision.created", {"projectId": project["projectId"], "revision": project["revision"]}, actor="project-service", tenant_id=tenant_id, site_id=site_id, machine_id=machine_id, correlation_id=message.correlationId, causation_id=message.messageId, idempotency_key=f"project-revision:{project['projectId']}:{project['revision']}"))
        return str(path)

    def get_revision(self, revision: str) -> dict[str, Any]:
        return self.store.load(revision)
