from __future__ import annotations

from dataclasses import dataclass


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class Actor:
    actor_id: str
    role: str
    tenant_id: str
    project_ids: frozenset[str] = frozenset()


ROLE_ACTIONS = {
    "viewer": {"READ"},
    "engineer": {"READ", "COMMENT", "SUGGEST", "MODIFY"},
    "reviewer": {"READ", "COMMENT", "SUGGEST", "MODIFY", "APPROVE"},
    "qa": {"READ", "COMMENT", "SUGGEST", "MODIFY", "APPROVE"},
    "owner": {"READ", "COMMENT", "SUGGEST", "MODIFY", "APPROVE", "RELEASE", "APPLY"},
    "ai": {"READ", "COMMENT", "SUGGEST", "MODIFY"},
}


def authorize(actor: Actor, action: str, *, tenant_id: str, project_id: str | None = None) -> None:
    if actor.tenant_id != tenant_id:
        raise AuthorizationError("PM-AUTH-001: tenant scope denied")
    if project_id and actor.project_ids and project_id not in actor.project_ids:
        raise AuthorizationError("PM-AUTH-002: project scope denied")
    if action not in ROLE_ACTIONS.get(actor.role, set()) or action in {"DEPLOY", "FORCE"} and actor.role == "ai":
        raise AuthorizationError(f"PM-AUTH-003: action denied: {action}")
