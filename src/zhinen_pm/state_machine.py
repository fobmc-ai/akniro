from __future__ import annotations

TRANSITIONS = {
    "requirement": {
        "DRAFT": {"READY"}, "READY": {"IMPLEMENTING", "BLOCKED"},
        "IMPLEMENTING": {"VERIFIED", "BLOCKED"}, "VERIFIED": {"ACCEPTED", "BLOCKED"},
        "ACCEPTED": {"CLOSED"}, "BLOCKED": {"READY", "IMPLEMENTING"}, "CLOSED": set(),
    },
    "work_item": {
        "PLANNED": {"IN_PROGRESS", "BLOCKED"}, "IN_PROGRESS": {"REVIEW", "BLOCKED"},
        "REVIEW": {"TEST", "IN_PROGRESS"}, "TEST": {"DONE", "BLOCKED"},
        "BLOCKED": {"PLANNED", "IN_PROGRESS"}, "DONE": set(),
    },
    "issue": {
        "OPEN": {"REPRODUCED", "BLOCKED"}, "REPRODUCED": {"ROOT_CAUSED", "BLOCKED"},
        "ROOT_CAUSED": {"FIXED", "BLOCKED"}, "FIXED": {"REGRESSION", "BLOCKED"},
        "REGRESSION": {"CLOSED", "FIXED"}, "BLOCKED": {"OPEN", "REPRODUCED"}, "CLOSED": set(),
    },
    "design_goal": {"DRAFT": {"READY", "BLOCKED"}, "READY": {"IMPLEMENTING", "BLOCKED"}, "IMPLEMENTING": {"VERIFIED", "BLOCKED"}, "VERIFIED": {"ACCEPTED", "BLOCKED"}, "ACCEPTED": {"CLOSED"}, "BLOCKED": {"READY", "IMPLEMENTING"}, "CLOSED": set()},
    "adr": {"PROPOSED": {"REVIEW", "BLOCKED"}, "REVIEW": {"ACCEPTED", "PROPOSED"}, "ACCEPTED": {"SUPERSEDED"}, "BLOCKED": {"PROPOSED"}, "SUPERSEDED": set()},
    "test_case": {"DRAFT": {"READY", "BLOCKED"}, "READY": {"RUNNING", "BLOCKED"}, "RUNNING": {"PASSED", "FAILED", "BLOCKED"}, "FAILED": {"READY", "RUNNING"}, "PASSED": {"ARCHIVED"}, "BLOCKED": {"READY"}, "ARCHIVED": set()},
    "knowledge": {"DRAFT": {"REVIEW", "BLOCKED"}, "REVIEW": {"VALIDATED", "DRAFT"}, "VALIDATED": {"APPROVED", "REVIEW"}, "APPROVED": {"EXPIRED", "DEPRECATED"}, "EXPIRED": {"REVIEW"}, "DEPRECATED": set(), "BLOCKED": {"DRAFT"}},
    "release": {"DRAFT": {"CANDIDATE", "BLOCKED"}, "CANDIDATE": {"VALIDATED", "DRAFT"}, "VALIDATED": {"APPROVED", "CANDIDATE"}, "APPROVED": {"RELEASED", "BLOCKED"}, "RELEASED": {"ROLLED_BACK", "SUPERSEDED"}, "BLOCKED": {"CANDIDATE"}, "ROLLED_BACK": set(), "SUPERSEDED": set()},
    "test_plan": {"DRAFT": {"READY", "BLOCKED"}, "READY": {"RUNNING", "BLOCKED"}, "RUNNING": {"COMPLETED", "FAILED", "BLOCKED"}, "FAILED": {"READY"}, "COMPLETED": {"ARCHIVED"}, "BLOCKED": {"READY"}, "ARCHIVED": set()},
    "test_run": {"QUEUED": {"RUNNING", "BLOCKED"}, "RUNNING": {"PASSED", "FAILED", "BLOCKED"}, "FAILED": {"QUEUED"}, "PASSED": {"ARCHIVED"}, "BLOCKED": {"QUEUED"}, "ARCHIVED": set()},
    "evidence": {"DRAFT": {"VALIDATED", "BLOCKED"}, "VALIDATED": {"ARCHIVED"}, "BLOCKED": {"DRAFT"}, "ARCHIVED": set()},
    "tool_validation": {"DRAFT": {"RUNNING", "BLOCKED"}, "RUNNING": {"VALIDATED", "FAILED", "BLOCKED"}, "FAILED": {"DRAFT"}, "VALIDATED": {"EXPIRED"}, "EXPIRED": {"DRAFT"}, "BLOCKED": {"DRAFT"}},
    "artifact": {"DRAFT": {"BUILT", "BLOCKED"}, "BUILT": {"TESTED", "DRAFT"}, "TESTED": {"APPROVED", "BLOCKED"}, "APPROVED": {"ARCHIVED"}, "BLOCKED": {"DRAFT"}, "ARCHIVED": set()},
    "parameter_snapshot": {"DRAFT": {"VALIDATED", "BLOCKED"}, "VALIDATED": {"APPROVED", "BLOCKED"}, "APPROVED": {"APPLIED", "ROLLED_BACK"}, "APPLIED": {"ROLLED_BACK"}, "BLOCKED": {"DRAFT"}, "ROLLED_BACK": set()},
    "maintenance": {"OPEN": {"IN_PROGRESS", "BLOCKED"}, "IN_PROGRESS": {"COMPLETED", "BLOCKED"}, "COMPLETED": {"CLOSED"}, "BLOCKED": {"OPEN"}, "CLOSED": set()},
    "deployment": {"REQUESTED": {"AUTHORIZED", "BLOCKED"}, "AUTHORIZED": {"STAGED", "BLOCKED"}, "STAGED": {"APPLIED", "BLOCKED"}, "APPLIED": {"OBSERVED", "ROLLED_BACK", "BLOCKED"}, "OBSERVED": {"CONFIRMED", "ROLLED_BACK", "BLOCKED"}, "CONFIRMED": set(), "ROLLED_BACK": set(), "BLOCKED": {"REQUESTED"}},
    "machine_commit": {"DRAFT": {"BUILT", "BLOCKED"}, "BUILT": {"VERIFIED", "DRAFT", "BLOCKED"}, "VERIFIED": {"RELEASED", "BLOCKED"}, "RELEASED": {"ROLLED_BACK", "SUPERSEDED"}, "ROLLED_BACK": set(), "SUPERSEDED": set(), "BLOCKED": {"DRAFT"}},
}


class InvalidTransition(ValueError):
    pass


def assert_transition(entity_type: str, current: str, target: str) -> None:
    try:
        allowed = TRANSITIONS[entity_type][current]
    except KeyError as exc:
        raise InvalidTransition(f"unknown state: {entity_type}/{current}") from exc
    if target not in allowed:
        raise InvalidTransition(f"PM-STATE-001: {entity_type} cannot transition {current}->{target}")
