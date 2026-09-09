from __future__ import annotations

from typing import Any


def build_context(store: Any, *, project_id: str, object_ids: list[str], actor_id: str) -> dict[str, Any]:
    if len(object_ids) > 20:
        raise ValueError("AI context is limited to 20 objects")
    objects = []
    omitted = []
    minimum_status = {
        "knowledge": {"APPROVED"}, "evidence": {"VALIDATED"}, "test_run": {"PASSED"},
        "artifact": {"APPROVED", "ARCHIVED"}, "parameter_snapshot": {"APPROVED", "APPLIED"},
        "maintenance": {"COMPLETED", "CLOSED"}, "release": {"APPROVED", "RELEASED"},
        "test_plan": {"COMPLETED"},
    }
    for object_id in object_ids:
        entity = store.get_entity(object_id)
        if entity["project_id"] != project_id:
            raise PermissionError("PM-AI-001: cross-project context denied")
        allowed_statuses = minimum_status.get(entity["entity_type"])
        if allowed_statuses is not None and entity["status"] not in allowed_statuses:
            omitted.append({"id": entity["id"], "reason": "status_not_approved_or_validated"})
            continue
        objects.append(entity)
    return {"actorId": actor_id, "projectId": project_id, "objects": objects, "omitted": omitted, "allowedActions": ["READ", "COMMENT", "SUGGEST"], "deniedActions": ["APPROVE", "RELEASE", "DEPLOY", "FORCE"]}
