from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
