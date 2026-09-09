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
