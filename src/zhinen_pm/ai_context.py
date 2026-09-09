from __future__ import annotations

from typing import Any


def build_context(store: Any, *, project_id: str, object_ids: list[str], actor_id: str) -> dict[str, Any]:
    if len(object_ids) > 20:
        raise ValueError("AI context is limited to 20 objects")
    objects = []
    for object_id in object_ids:
        entity = store.get_entity(object_id)
        if entity["project_id"] != project_id:
            raise PermissionError("PM-AI-001: cross-project context denied")
        if entity["entity_type"] == "knowledge" and entity["status"] != "APPROVED":
            continue
        objects.append(entity)
    return {"actorId": actor_id, "projectId": project_id, "objects": objects, "allowedActions": ["READ", "COMMENT", "SUGGEST"], "deniedActions": ["APPROVE", "RELEASE", "DEPLOY", "FORCE"]}
