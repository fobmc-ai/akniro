"""Small, deterministic V0.1 Machine Project contract validator.

This is intentionally narrower than a general JSON Schema engine. It validates
the current Machine Project contract and keeps error paths stable for callers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_KEYS = {"schemaVersion", "projectId", "name", "revision", "machineId", "capabilities", "components"}
CAPABILITY_KEYS = {"capabilityId", "version", "status", "provider", "prerequisites", "license", "resourceProfile"}
COMPONENT_KEYS = {"componentId", "kind", "version", "source", "criticality"}
CAPABILITY_ID = re.compile(r"^[a-z][a-z0-9]*(\.[a-z0-9-]+){1,5}$")
OBJECT_ID = re.compile(r"^[A-Z0-9-]{3,64}$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
REVISION = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


class ProjectValidationError(ValueError):
    """Validation failure with a machine-readable JSON path."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


def _require(condition: bool, path: str, message: str) -> None:
    if not condition:
        raise ProjectValidationError(path, message)


def _string(value: Any, path: str, *, pattern: re.Pattern[str] | None = None, min_length: int = 0) -> None:
    _require(isinstance(value, str), path, "must be a string")
    _require(len(value) >= min_length, path, "must not be empty")
    if pattern:
        _require(bool(pattern.fullmatch(value)), path, "has invalid format")


def _object(value: Any, path: str, allowed: set[str], required: set[str]) -> None:
    _require(isinstance(value, dict), path, "must be an object")
    unknown = set(value) - allowed
    _require(not unknown, path, f"unknown fields: {', '.join(sorted(unknown))}")
    missing = required - set(value)
    _require(not missing, path, f"missing fields: {', '.join(sorted(missing))}")


def validate_project(project: Any) -> dict[str, Any]:
    """Validate and return a project without mutating it."""
    _object(project, "$", PROJECT_KEYS, {"schemaVersion", "projectId", "name", "revision", "capabilities", "components"})
    _require(project["schemaVersion"] == "0.1", "$.schemaVersion", "must equal 0.1")
    _string(project["projectId"], "$.projectId", pattern=OBJECT_ID)
    _string(project["name"], "$.name", min_length=1)
    _string(project["revision"], "$.revision", pattern=REVISION)
    if "machineId" in project:
        _string(project["machineId"], "$.machineId", pattern=OBJECT_ID)

    _require(isinstance(project["capabilities"], list), "$.capabilities", "must be an array")
    capability_ids: set[str] = set()
    for index, capability in enumerate(project["capabilities"]):
        path = f"$.capabilities[{index}]"
        _object(capability, path, CAPABILITY_KEYS, {"capabilityId", "version", "status", "provider"})
        _string(capability["capabilityId"], f"{path}.capabilityId", pattern=CAPABILITY_ID)
        _require(capability["capabilityId"] not in capability_ids, f"{path}.capabilityId", "duplicate capability ID")
        capability_ids.add(capability["capabilityId"])
        _string(capability["version"], f"{path}.version", pattern=SEMVER)
        _require(capability["status"] in {"proposed", "experimental", "stable", "deprecated", "retired"}, f"{path}.status", "invalid lifecycle status")
        _string(capability["provider"], f"{path}.provider", min_length=1)
        if "prerequisites" in capability:
            _require(isinstance(capability["prerequisites"], list) and all(isinstance(x, str) for x in capability["prerequisites"]), f"{path}.prerequisites", "must be an array of strings")

    _require(isinstance(project["components"], list), "$.components", "must be an array")
    component_ids: set[str] = set()
    allowed_kinds = {"plc", "hmi", "vision", "motion", "robot", "scada", "mes", "ai", "driver"}
    for index, component in enumerate(project["components"]):
        path = f"$.components[{index}]"
        _object(component, path, COMPONENT_KEYS, {"componentId", "kind", "version"})
        _string(component["componentId"], f"{path}.componentId", pattern=OBJECT_ID)
        _require(component["componentId"] not in component_ids, f"{path}.componentId", "duplicate component ID")
        component_ids.add(component["componentId"])
        _require(component["kind"] in allowed_kinds, f"{path}.kind", "invalid component kind")
        _string(component["version"], f"{path}.version", pattern=REVISION)
        if "criticality" in component:
            _require(component["criticality"] in {"normal", "critical", "safety"}, f"{path}.criticality", "invalid criticality")
    return project


def load_project(path: str | Path) -> dict[str, Any]:
    """Load a JSON Machine Project and validate it."""
    file_path = Path(path)
    try:
        project = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectValidationError("$", f"invalid JSON: {exc.msg}") from exc
    return validate_project(project)
