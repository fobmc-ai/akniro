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
    EngineeringCapability("LIFE-001", "生产质量与维护生命周期", "LIFECYCLE", "SIMULATED", "HUMAN_APPROVAL_REQUIRED", ("production_metrics", "quality_metrics", "maintenance_workflow")),
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
    validation = {"capabilityId": capability.id, "result": result, "missing": missing, "simulated": capability.mode == "SIMULATED", "safetyGate": capability.safety_gate}
    import json
    validation["validationHash"] = "sha256:" + hashlib.sha256(json.dumps(validation, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    validation["validatedAt"] = datetime.now(timezone.utc).isoformat()
    return validation


def simulation_evidence(capability_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = validate_capability(capability_id, payload)
    diagnostics = {
        "PLC-001": ("compile", "source_present", "toolchain_pinned", "deterministic_build"),
        "PLC-002": ("runtime", "cycle_time", "watchdog", "safe_stop"),
        "HMI-001": ("binding", "tag_binding", "alarm_binding", "screen_smoke"),
        "EDA-001": ("consistency", "io_consistency", "bom_consistency"),
        "MOT-001": ("axis", "axis_simulation", "limit_check", "state_machine"),
        "VIS-001": ("dataset", "dataset_hash", "thresholds", "regression_set"),
        "ROB-001": ("handshake", "handshake", "permission_scope", "fault_recovery"),
        "FW-001": ("firmware", "binary_hash", "power_recovery", "rollback"),
        "EDGE-001": ("sync", "offline_queue", "replay_idempotency", "conflict"),
        "COMM-001": ("acceptance", "checklist", "evidence", "signoff"),
        "LIFE-001": ("lifecycle", "production_metrics", "quality_metrics", "maintenance_workflow"),
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
    if capability_id == "EDA-001" and payload.get("io_expected") is not None and payload.get("io_actual") is not None:
        eda = simulate_eda_consistency(payload["io_expected"], payload["io_actual"])
        result["eda"] = eda
        if eda["result"] != "PASSED":
            domain_errors.append("io_consistency_failed")
    if capability_id == "HMI-001" and payload.get("tag_ids") is not None and payload.get("bound_tag_ids") is not None:
        expected_tags = set(payload["tag_ids"])
        actual_tags = set(payload["bound_tag_ids"])
        if expected_tags - actual_tags:
            domain_errors.append("hmi_missing_tags:" + ",".join(sorted(expected_tags - actual_tags)))
        if actual_tags - expected_tags:
            domain_errors.append("hmi_unknown_tags:" + ",".join(sorted(actual_tags - expected_tags)))
    if capability_id == "HMI-001" and payload.get("screen_sequence") is not None:
        hmi = simulate_hmi_screens(payload.get("expected_screens", []), payload["screen_sequence"])
        result["hmi"] = hmi
        if hmi["result"] != "PASSED":
            domain_errors.append(hmi["reason"])
    if capability_id == "MOT-001" and payload.get("soft_limit_min") is not None and payload.get("soft_limit_max") is not None and payload["soft_limit_min"] >= payload["soft_limit_max"]:
        domain_errors.append("invalid_soft_limits")
    if capability_id == "MOT-001" and all(key in payload for key in ("position", "target_position", "velocity", "soft_limit_min", "soft_limit_max")):
        motion = simulate_motion_axis(float(payload["position"]), float(payload["target_position"]), float(payload["velocity"]), float(payload["soft_limit_min"]), float(payload["soft_limit_max"]))
        result["motion"] = motion
        if motion["result"] != "PASSED":
            domain_errors.append(motion["reason"])
    if capability_id == "VIS-001":
        thresholds = payload.get("threshold_values", [])
        if thresholds and any(not isinstance(x, (int, float)) or x < 0 or x > 1 for x in thresholds):
            domain_errors.append("threshold_out_of_range")
        if payload.get("expected_labels") is not None or payload.get("predicted_labels") is not None:
            vision = simulate_vision_algorithm(payload.get("expected_labels", []), payload.get("predicted_labels", []))
            result["vision"] = vision
            if vision["result"] != "PASSED":
                domain_errors.append(vision["reason"])
    if capability_id == "FW-001" and payload.get("binary_hash") and not str(payload["binary_hash"]).startswith("sha256:"):
        domain_errors.append("binary_hash_not_sha256")
    if capability_id == "EDGE-001" and payload.get("duplicate_event_ids"):
        domain_errors.append("replay_not_idempotent")
    if capability_id == "EDGE-001" and payload.get("event_ids") is not None:
        edge = simulate_edge_replay(payload["event_ids"], bool(payload.get("replay_idempotency")))
        result["edge"] = edge
        if edge["result"] != "PASSED":
            domain_errors.append(edge["reason"])
    if capability_id == "ROB-001" and payload.get("handshake_sequence") is not None and payload["handshake_sequence"] != ["INIT", "READY", "START", "DONE"]:
        domain_errors.append("handshake_sequence_invalid")
    if capability_id == "COMM-001" and payload.get("checklist_items") is not None and any(not item.get("passed") for item in payload["checklist_items"]):
        domain_errors.append("commissioning_checklist_incomplete")
    if capability_id == "COMM-001" and payload.get("checklist_sequence") is not None:
        commissioning = simulate_commissioning_checklist(payload.get("checklist_sequence", []), payload.get("checklist_items", []))
        result["commissioning"] = commissioning
        if commissioning["result"] != "PASSED":
            domain_errors.append(commissioning["reason"])
    if capability_id == "LIFE-001" and payload.get("metric_values") is not None and any(not isinstance(value, (int, float)) or value < 0 for value in payload["metric_values"]):
        domain_errors.append("lifecycle_metric_invalid")
    if capability_id == "LIFE-001" and all(key in payload for key in ("planned_minutes", "downtime_minutes", "total_count", "good_count", "ideal_cycle_seconds")):
        lifecycle = simulate_oee_metrics(float(payload["planned_minutes"]), float(payload["downtime_minutes"]), int(payload["total_count"]), int(payload["good_count"]), float(payload["ideal_cycle_seconds"]))
        result["lifecycle"] = lifecycle
        if lifecycle["result"] != "PASSED":
            domain_errors.append(lifecycle["reason"])
    if capability_id == "LIFE-001" and payload.get("spc_values") is not None:
        spc = simulate_spc_metrics(payload.get("spc_values", []), payload.get("spc_lower"), payload.get("spc_upper"))
        result["spc"] = spc
        if spc["result"] != "PASSED":
            domain_errors.append(spc["reason"])
    if capability_id == "LIFE-001" and payload.get("health_signals") is not None:
        health = simulate_health_check(payload.get("health_signals", {}), payload.get("health_limits", {}))
        result["health"] = health
        if health["result"] != "PASSED":
            domain_errors.append(health["reason"])
    if capability_id == "LIFE-001" and payload.get("product_trace") is not None:
        product_trace = simulate_product_trace(payload.get("product_trace", {}))
        result["productTrace"] = product_trace
        if product_trace["result"] != "PASSED":
            domain_errors.append(product_trace["reason"])
    if capability_id == "PLC-002":
        runtime = simulate_plc_runtime(int(payload.get("cycles", 100)), int(payload.get("cycle_ms", 10)), int(payload.get("watchdog_ms", 50)), payload.get("injected_fault"))
        result["runtime"] = runtime
        if runtime["result"] != "PASSED":
            domain_errors.append(runtime.get("reason") or runtime.get("fault") or "runtime_failed")
    if domain_errors:
        result["result"] = "FAILED"
        result["missing"] = sorted(set(result.get("missing", []) + domain_errors))
    result["domainErrors"] = domain_errors
    result["traceHash"] = hashlib.sha256(jsonable_trace(capability_id, payload, result).encode("utf-8")).hexdigest()
    result["evidenceType"] = "SIMULATION_RESULT"
    result["deterministic"] = True
    result["testPlan"] = f"{capability_id}:golden-validation"
    import json
    stable_result = {key: value for key, value in result.items() if key not in {"validatedAt", "validationHash"}}
    result["validationHash"] = "sha256:" + hashlib.sha256(json.dumps(stable_result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return result


def jsonable_trace(capability_id: str, payload: dict[str, Any], result: dict[str, Any]) -> str:
    """Return a stable, non-secret trace input for deterministic evidence hashing."""
    import json
    trace = {"capabilityId": capability_id, "checks": result.get("checks", []), "domainErrors": result.get("domainErrors", []), "fault": payload.get("injected_fault")}
    return json.dumps(trace, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def simulate_motion_axis(position: float, target_position: float, velocity: float, soft_limit_min: float, soft_limit_max: float) -> dict[str, Any]:
    if velocity <= 0 or soft_limit_min >= soft_limit_max or not (soft_limit_min <= position <= soft_limit_max):
        return {"result": "BLOCKED", "reason": "invalid_axis_limits", "safeStop": True, "deterministic": True}
    if not soft_limit_min <= target_position <= soft_limit_max:
        return {"result": "FAILED", "reason": "target_outside_soft_limits", "safeStop": True, "deterministic": True}
    distance = abs(target_position - position)
    steps = int(distance / velocity) + (1 if distance % velocity else 0)
    trajectory = [round(position + (target_position - position) * index / max(steps, 1), 6) for index in range(steps + 1)]
    return {"result": "PASSED", "start": position, "target": target_position, "velocity": velocity, "steps": steps, "trajectory": trajectory, "safeStop": False, "deterministic": True}


def simulate_vision_algorithm(expected_labels: list[Any], predicted_labels: list[Any]) -> dict[str, Any]:
    if not expected_labels or len(expected_labels) != len(predicted_labels):
        return {"result": "BLOCKED", "reason": "label_set_invalid", "deterministic": True}
    tp = sum(1 for expected, predicted in zip(expected_labels, predicted_labels) if expected == 1 and predicted == 1)
    tn = sum(1 for expected, predicted in zip(expected_labels, predicted_labels) if expected == 0 and predicted == 0)
    fp = sum(1 for expected, predicted in zip(expected_labels, predicted_labels) if expected == 0 and predicted == 1)
    fn = sum(1 for expected, predicted in zip(expected_labels, predicted_labels) if expected == 1 and predicted == 0)
    total = len(expected_labels)
    return {"result": "PASSED" if tp + tn == total else "FAILED", "samples": total, "confusionMatrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn}, "accuracy": round((tp + tn) / total, 6), "deterministic": True, "reason": "classification_mismatch" if tp + tn != total else None}


def simulate_edge_replay(event_ids: list[str], idempotent: bool) -> dict[str, Any]:
    if not event_ids:
        return {"result": "BLOCKED", "reason": "empty_event_queue", "deterministic": True}
    duplicates = len(event_ids) - len(set(event_ids))
    if duplicates and not idempotent:
        return {"result": "FAILED", "reason": "replay_not_idempotent", "events": len(event_ids), "duplicates": duplicates, "applied": len(event_ids), "deterministic": True}
    return {"result": "PASSED", "events": len(event_ids), "duplicates": duplicates, "applied": len(set(event_ids)), "skipped": duplicates, "deterministic": True, "reason": None}


def validate_toolchain_matrix(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in cases:
        passed = bool(case.get("compilePassed")) and bool(case.get("hmiSmoke", True)) and case.get("expectedHash") == case.get("actualHash")
        rows.append({"id": case.get("id", "UNKNOWN"), "toolchain": case.get("toolchain", "TBD"), "passed": passed, "reason": None if passed else "golden_project_mismatch"})
    return {"result": "PASSED" if rows and all(row["passed"] for row in rows) else "FAILED", "cases": rows, "passed": sum(1 for row in rows if row["passed"]), "total": len(rows), "deterministic": True, "matrixHash": hashlib.sha256(jsonable_matrix(rows).encode("utf-8")).hexdigest()}


def jsonable_matrix(rows: list[dict[str, Any]]) -> str:
    import json
    return json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def simulate_eda_consistency(expected: list[str], actual: list[str]) -> dict[str, Any]:
    expected_set, actual_set = set(expected), set(actual)
    duplicates = sorted({item for item in actual if actual.count(item) > 1})
    missing, extra = sorted(expected_set - actual_set), sorted(actual_set - expected_set)
    failed = bool(missing or extra or duplicates)
    return {"result": "FAILED" if failed else "PASSED", "expected": len(expected), "actual": len(actual), "missing": missing, "extra": extra, "duplicates": duplicates, "deterministic": True}


def simulate_hmi_screens(expected_screens: list[str], visited_screens: list[str]) -> dict[str, Any]:
    missing = [screen for screen in expected_screens if screen not in visited_screens]
    unexpected = [screen for screen in visited_screens if screen not in expected_screens]
    in_order = [screen for screen in visited_screens if screen in expected_screens] == expected_screens
    failed = bool(missing or unexpected or not in_order)
    return {"result": "FAILED" if failed else "PASSED", "expected": expected_screens, "visited": visited_screens, "missing": missing, "unexpected": unexpected, "inOrder": in_order, "deterministic": True, "reason": "screen_smoke_failed" if failed else None}


def simulate_commissioning_checklist(sequence: list[str], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate the governed FAT/SAT commissioning order and step evidence."""
    expected = ["24V", "Network", "EtherCAT", "IO", "Safety", "Servo", "Cylinder", "Vision", "Station", "Auto Cycle", "Burn-in"]
    if not isinstance(sequence, list) or not sequence:
        return {"result": "BLOCKED", "reason": "commissioning_sequence_missing", "expected": expected, "actual": sequence, "deterministic": True}
    order_ok = sequence == expected
    item_map = {item.get("id"): item for item in items if isinstance(item, dict)}
    missing_steps = [step for step in expected if step not in item_map]
    failed_steps = [step for step in expected if step in item_map and not item_map[step].get("passed")]
    if not order_ok:
        return {"result": "FAILED", "reason": "commissioning_sequence_invalid", "expected": expected, "actual": sequence, "missingSteps": missing_steps, "failedSteps": failed_steps, "deterministic": True}
    if missing_steps or failed_steps:
        return {"result": "FAILED", "reason": "commissioning_evidence_incomplete", "expected": expected, "actual": sequence, "missingSteps": missing_steps, "failedSteps": failed_steps, "deterministic": True}
    return {"result": "PASSED", "expected": expected, "actual": sequence, "missingSteps": [], "failedSteps": [], "deterministic": True, "reason": None}


def simulate_oee_metrics(planned_minutes: float, downtime_minutes: float, total_count: int, good_count: int, ideal_cycle_seconds: float) -> dict[str, Any]:
    if planned_minutes <= 0 or downtime_minutes < 0 or downtime_minutes > planned_minutes or total_count < 0 or good_count < 0 or good_count > total_count or ideal_cycle_seconds <= 0:
        return {"result": "BLOCKED", "reason": "lifecycle_metric_invalid", "deterministic": True}
    run_minutes = planned_minutes - downtime_minutes
    availability = run_minutes / planned_minutes
    performance = (ideal_cycle_seconds * total_count / 60) / run_minutes if run_minutes else 0
    quality = good_count / total_count if total_count else 0
    return {"result": "PASSED", "availability": round(availability, 6), "performance": round(performance, 6), "quality": round(quality, 6), "oee": round(availability * performance * quality, 6), "deterministic": True, "reason": None}


def simulate_spc_metrics(values: list[float], lower: float | None, upper: float | None) -> dict[str, Any]:
    """Evaluate a deterministic individual-value SPC control band."""
    if not values or lower is None or upper is None or lower >= upper or any(not isinstance(value, (int, float)) for value in values):
        return {"result": "BLOCKED", "reason": "spc_limits_or_samples_invalid", "deterministic": True}
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    out_of_control = [index for index, value in enumerate(values) if value < lower or value > upper]
    return {"result": "FAILED" if out_of_control else "PASSED", "samples": len(values), "mean": round(mean, 6), "sigma": round(variance ** 0.5, 6), "limits": {"lower": lower, "upper": upper}, "outOfControl": out_of_control, "deterministic": True, "reason": "spc_out_of_control" if out_of_control else None}


def simulate_health_check(signals: dict[str, float], limits: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Check sorted device health signals against explicit operating limits."""
    if not signals or not limits or any(name not in limits for name in signals):
        return {"result": "BLOCKED", "reason": "health_signal_limits_invalid", "deterministic": True}
    violations = []
    checks = []
    for name in sorted(signals):
        value = signals[name]
        bound = limits[name]
        lower = bound.get("min") if isinstance(bound, dict) else None
        upper = bound.get("max") if isinstance(bound, dict) else None
        valid = isinstance(value, (int, float)) and isinstance(lower, (int, float)) and isinstance(upper, (int, float)) and lower <= upper and lower <= value <= upper
        checks.append({"name": name, "value": value, "min": lower, "max": upper, "passed": valid})
        if not valid:
            violations.append(name)
    return {"result": "FAILED" if violations else "PASSED", "checks": checks, "violations": violations, "deterministic": True, "reason": "health_limit_exceeded" if violations else None}


def simulate_product_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Validate a stable product-to-machine genealogy record without live historian access."""
    required = ("productId", "machineId", "recipeId", "plcState", "measurement", "parameters", "timestamp")
    missing = [field for field in required if trace.get(field) in (None, "", {})]
    if missing:
        return {"result": "BLOCKED", "reason": "product_trace_fields_missing", "missing": missing, "deterministic": True}
    if not isinstance(trace["measurement"], dict) or not isinstance(trace["parameters"], dict):
        return {"result": "BLOCKED", "reason": "product_trace_measurement_invalid", "missing": [], "deterministic": True}
    import json
    canonical = json.dumps({key: trace[key] for key in required}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"result": "PASSED", "productId": trace["productId"], "machineId": trace["machineId"], "recipeId": trace["recipeId"], "plcState": trace["plcState"], "measurement": trace["measurement"], "parameters": trace["parameters"], "timestamp": trace["timestamp"], "traceHash": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(), "deterministic": True, "reason": None}


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


def simulate_plc_download(*, artifact_id: str, artifact_hash: str, artifact_status: str, target_machine_id: str, approval_id: str | None, rollback_revision: str | None) -> dict[str, Any]:
    """Create a deterministic download manifest without touching a controller."""
    errors = []
    if not artifact_id or not artifact_hash.startswith("sha256:"):
        errors.append("artifact_hash_invalid")
    if artifact_status != "APPROVED":
        errors.append("artifact_not_human_approved")
    if not target_machine_id:
        errors.append("target_machine_required")
    if not approval_id:
        errors.append("approval_required")
    if not rollback_revision:
        errors.append("rollback_revision_required")
    transfer_hash = hashlib.sha256(f"{artifact_id}:{artifact_hash}:{target_machine_id}:{rollback_revision or ''}".encode("utf-8")).hexdigest()
    return {"result": "BLOCKED" if errors else "READY_FOR_EDGE", "artifactId": artifact_id, "targetMachineId": target_machine_id, "artifactHash": artifact_hash, "transferHash": f"sha256:{transfer_hash}", "approvalId": approval_id, "rollbackRevision": rollback_revision, "errors": errors, "writesController": False, "humanApprovalRequired": True, "deterministic": True}


def simulate_plc_monitor(*, tags: dict[str, Any], cycles: int = 10, fault: str | None = None) -> dict[str, Any]:
    """Return a stable online-monitor snapshot for deterministic software validation."""
    errors = []
    if cycles < 1 or cycles > 10000:
        errors.append("cycles_out_of_range")
    if not isinstance(tags, dict) or not tags:
        errors.append("tags_required")
    if fault and fault not in {"communication_loss", "watchdog", "safety_trip"}:
        errors.append("unknown_fault")
    snapshot = [{"name": name, "value": tags[name], "quality": "BAD" if fault else "GOOD"} for name in sorted(tags)] if isinstance(tags, dict) else []
    return {"result": "FAILED" if errors or fault else "PASSED", "cycles": cycles, "fault": fault, "safeStop": bool(fault), "tags": snapshot, "errors": errors + ([fault] if fault else []), "realtimeSource": "SIMULATION", "deterministic": True}


def build_firmware_image(source: str, toolchain_version: str = "SIMULATED-FW-0.1", target: str = "EDGE", previous_hash: str | None = None, inject_power_loss: bool = False) -> dict[str, Any]:
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    errors: list[str] = []
    if not source.strip():
        errors.append("empty_source")
    if "UNSAFE_BOOT" in source:
        errors.append("unsafe_boot_requires_manual_review")
    image_hash = hashlib.sha256(f"{source_hash}:{toolchain_version}:{target}".encode("utf-8")).hexdigest()
    recovery = "ROLLBACK_TO_PREVIOUS" if inject_power_loss and previous_hash else ("RECOVERY_UNAVAILABLE" if inject_power_loss else "NOT_INJECTED")
    if inject_power_loss and not previous_hash:
        errors.append("power_loss_without_previous_image")
    return {"result": "FAILED" if errors else "PASSED", "sourceHash": f"sha256:{source_hash}", "imageHash": f"sha256:{image_hash}", "toolchainVersion": toolchain_version, "target": target, "errors": errors, "powerRecovery": recovery, "rollbackHash": previous_hash, "deterministic": True, "log": "FIRMWARE SIMULATED BUILD OK" if not errors else "FIRMWARE SIMULATED BUILD FAILED"}


def simulate_plc_runtime(cycles: int = 100, cycle_ms: int = 10, watchdog_ms: int = 50, injected_fault: str | None = None) -> dict[str, Any]:
    if cycles < 1 or cycle_ms < 1 or watchdog_ms < cycle_ms:
        return {"result": "BLOCKED", "reason": "invalid_runtime_limits", "safeStop": True}
    fault = injected_fault in {"watchdog", "communication_loss", "safety_trip"}
    max_cycle = watchdog_ms + 1 if injected_fault == "watchdog" else cycle_ms
    return {"result": "FAILED" if fault else "PASSED", "cycles": cycles, "cycleMs": cycle_ms, "maxObservedCycleMs": max_cycle, "watchdogMs": watchdog_ms, "fault": injected_fault, "safeStop": fault, "deterministic": True, "target": "SIMULATION"}
