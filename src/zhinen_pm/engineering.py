from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any


@dataclass(frozen=True)
class EngineeringCapability:
    id: str
    name: str
    domain: str
    mode: str
    safety_gate: str
    checks: tuple[str, ...]


CAPABILITIES = (
    EngineeringCapability("PLC-001", "PLC 工程与编译器", "PLC", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("source_present", "toolchain_pinned", "deterministic_build")),
    EngineeringCapability("PLC-002", "PLC Runtime", "PLC", "CONTRACT_ONLY", "HUMAN_APPROVAL_REQUIRED", ("cycle_time", "watchdog", "safe_stop")),
    EngineeringCapability("HMI-001", "HMI Designer 与标签绑定", "HMI", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("tag_binding", "alarm_binding", "screen_smoke")),
    EngineeringCapability("EDA-001", "EDA 与 IO/BOM", "EDA", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("io_consistency", "bom_consistency")),
    EngineeringCapability("MOT-001", "Motion / EtherCAT", "MOTION", "CONTRACT_ONLY", "HUMAN_APPROVAL_REQUIRED", ("axis_simulation", "limit_check", "state_machine")),
    EngineeringCapability("VIS-001", "Vision / Feeder", "VISION", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("dataset_hash", "thresholds", "regression_set")),
    EngineeringCapability("ROB-001", "Robot capability layer", "ROBOT", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("handshake", "permission_scope", "fault_recovery")),
    EngineeringCapability("FW-001", "Firmware 工程与升级", "FIRMWARE", "CONTRACT_ONLY", "HUMAN_APPROVAL_REQUIRED", ("binary_hash", "power_recovery", "rollback")),
    EngineeringCapability("EDGE-001", "Edge Agent 离线同步", "EDGE", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("offline_queue", "replay_idempotency", "conflict")),
    EngineeringCapability("COMM-001", "FAT / SAT 调试验收", "COMMISSIONING", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("checklist", "evidence", "signoff")),
    EngineeringCapability("ECO-001", "Marketplace / fleet learning", "ECOSYSTEM", "CONTRACT_ONLY", "HUMAN_APPROVAL_REQUIRED", ("consent", "scope", "retention")),
)


def list_capabilities() -> list[dict[str, Any]]:
    return [{"id": x.id, "name": x.name, "domain": x.domain, "mode": x.mode, "safetyGate": x.safety_gate, "checks": list(x.checks)} for x in CAPABILITIES]


def validate_capability(capability_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    capability = next((x for x in CAPABILITIES if x.id == capability_id), None)
    if capability is None:
        raise KeyError(f"unknown capability: {capability_id}")
    missing = [check for check in capability.checks if not payload.get(check)]
    result = "BLOCKED" if missing else "PASSED"
    if capability.mode == "CONTRACT_ONLY" and result == "PASSED":
        result = "CONTRACT_PASSED"
    return {"capabilityId": capability.id, "result": result, "missing": missing, "simulated": capability.mode == "SIMULATED", "safetyGate": capability.safety_gate, "validatedAt": datetime.now(timezone.utc).isoformat()}


def simulation_evidence(capability_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = validate_capability(capability_id, payload)
    diagnostics = {
        "PLC-001": ("compile", "source_present", "toolchain_pinned", "deterministic_build"),
        "HMI-001": ("binding", "tag_binding", "alarm_binding", "screen_smoke"),
        "EDA-001": ("consistency", "io_consistency", "bom_consistency"),
        "MOT-001": ("axis", "axis_simulation", "limit_check", "state_machine"),
        "VIS-001": ("dataset", "dataset_hash", "thresholds", "regression_set"),
        "ROB-001": ("handshake", "handshake", "permission_scope", "fault_recovery"),
        "FW-001": ("firmware", "binary_hash", "power_recovery", "rollback"),
        "EDGE-001": ("sync", "offline_queue", "replay_idempotency", "conflict"),
        "COMM-001": ("acceptance", "checklist", "evidence", "signoff"),
        "ECO-001": ("consent", "consent", "scope", "retention"),
    }
    descriptor = diagnostics.get(capability_id)
    if descriptor:
        result["diagnostic"] = descriptor[0]
        result["checks"] = [{"name": key, "passed": bool(payload.get(key))} for key in descriptor[1:]]
    if capability_id == "PLC-001" and payload.get("source") == "syntax_error":
        result["result"] = "FAILED"; result["missing"] = ["syntax_error"]
    if capability_id == "HMI-001" and payload.get("duplicate_tag"):
        result["result"] = "FAILED"; result["missing"] = ["duplicate_tag_resolution"]
    domain_errors: list[str] = []
    if capability_id == "EDA-001" and payload.get("io_expected") is not None and payload.get("io_actual") is not None and payload["io_expected"] != payload["io_actual"]:
        domain_errors.append("io_bom_mismatch")
    if capability_id == "MOT-001" and payload.get("soft_limit_min") is not None and payload.get("soft_limit_max") is not None and payload["soft_limit_min"] >= payload["soft_limit_max"]:
        domain_errors.append("invalid_soft_limits")
    if capability_id == "VIS-001":
        thresholds = payload.get("threshold_values", [])
        if thresholds and any(not isinstance(x, (int, float)) or x < 0 or x > 1 for x in thresholds):
            domain_errors.append("threshold_out_of_range")
    if capability_id == "FW-001" and payload.get("binary_hash") and not str(payload["binary_hash"]).startswith("sha256:"):
        domain_errors.append("binary_hash_not_sha256")
    if capability_id == "EDGE-001" and payload.get("duplicate_event_ids"):
        domain_errors.append("replay_not_idempotent")
    if domain_errors:
        result["result"] = "FAILED"
        result["missing"] = sorted(set(result.get("missing", []) + domain_errors))
    result["domainErrors"] = domain_errors
    result["evidenceType"] = "SIMULATION_RESULT"
    result["deterministic"] = True
    result["testPlan"] = f"{capability_id}:golden-validation"
    return result


def build_plc_project(source: str, toolchain_version: str = "SIMULATED-PLC-0.1") -> dict[str, Any]:
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    errors = []
    if not source.strip():
        errors.append("empty_source")
    if "SYNTAX_ERROR" in source:
        errors.append("syntax_error")
    if "UNSAFE_FORCE" in source:
        errors.append("unsafe_force_requires_manual_review")
    build_hash = hashlib.sha256(f"{source_hash}:{toolchain_version}".encode("utf-8")).hexdigest()
    return {"result": "FAILED" if errors else "PASSED", "sourceHash": f"sha256:{source_hash}", "buildHash": f"sha256:{build_hash}", "toolchainVersion": toolchain_version, "errors": errors, "log": "PLC SIMULATED BUILD OK" if not errors else "PLC SIMULATED BUILD FAILED", "target": "SIMULATION"}


def simulate_plc_runtime(cycles: int = 100, cycle_ms: int = 10, watchdog_ms: int = 50, injected_fault: str | None = None) -> dict[str, Any]:
    if cycles < 1 or cycle_ms < 1 or watchdog_ms < cycle_ms:
        return {"result": "BLOCKED", "reason": "invalid_runtime_limits", "safeStop": True}
    fault = injected_fault in {"watchdog", "communication_loss", "safety_trip"}
    max_cycle = watchdog_ms + 1 if injected_fault == "watchdog" else cycle_ms
    return {"result": "FAILED" if fault else "PASSED", "cycles": cycles, "cycleMs": cycle_ms, "maxObservedCycleMs": max_cycle, "watchdogMs": watchdog_ms, "fault": injected_fault, "safeStop": fault, "deterministic": True, "target": "SIMULATION"}
