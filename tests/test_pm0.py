import sys
import tempfile
import unittest
import urllib.request
import urllib.error
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_pm.authorization import Actor, AuthorizationError, authorize
from zhinen_pm.state_machine import InvalidTransition, assert_transition
from zhinen_pm.store import ProjectStore
from zhinen_pm.server import create_server
from zhinen_pm.engineering import validate_capability, list_capabilities, simulation_evidence, build_plc_project, build_firmware_image, simulate_plc_runtime, simulate_motion_axis, simulate_vision_algorithm, simulate_edge_replay, validate_toolchain_matrix, simulate_eda_consistency, simulate_hmi_screens, simulate_oee_metrics, simulate_spc_metrics, simulate_health_check, simulate_product_trace, simulate_commissioning_checklist, simulate_plc_download, simulate_plc_monitor, simulate_ecosystem_contract
from zhinen_pm.ai_context import build_context
import threading


class PM0Tests(unittest.TestCase):
    def test_state_machine_rejects_skipping_test(self):
        with self.assertRaises(InvalidTransition):
            assert_transition("work_item", "IN_PROGRESS", "DONE")

    def test_ai_cannot_deploy(self):
        with self.assertRaises(AuthorizationError):
            authorize(Actor("AI-001", "ai", "T-001", frozenset({"P-001"})), "DEPLOY", tenant_id="T-001", project_id="P-001")
        with self.assertRaises(AuthorizationError):
            authorize(Actor("AI-001", "ai", "T-001", frozenset({"P-001"})), "APPLY", tenant_id="T-001", project_id="P-001")

    def test_store_scope_revision_transition_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            entity = store.create_entity(entity_id="REQ-001", entity_type="requirement", project_id="P-001", tenant_id="T-001", title="Define MVP", owner_id="U-001", payload={"description":"MVP contract", "priority":"P0", "acceptanceCriteria":["pass"], "nonGoals":["field control"], "source":"product", "traceLinks":["MASTER_PLAN.md"]})
            self.assertEqual(entity["status"], "DRAFT")
            updated = store.transition(entity_id="REQ-001", target="READY", actor_id="U-001", expected_revision=1)
            self.assertEqual(updated["revision"], 2)
            with self.assertRaisesRegex(RuntimeError, "revision conflict"):
                store.transition(entity_id="REQ-001", target="IMPLEMENTING", actor_id="U-001", expected_revision=1)
            self.assertGreaterEqual(len(store.audit("P-001")), 2)
            store.close()

    def test_requirement_and_design_goal_ready_gates_require_contract_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            requirement = store.create_entity(entity_id="REQ-GATE", entity_type="requirement", project_id="P-001", tenant_id="T-001", title="Incomplete", owner_id="U-001")
            with self.assertRaisesRegex(ValueError, "PM-REQ-001"):
                store.transition(entity_id=requirement["id"], target="READY", actor_id="U-001", expected_revision=1)
            goal = store.create_entity(entity_id="DG-GATE", entity_type="design_goal", project_id="P-001", tenant_id="T-001", title="Incomplete goal", owner_id="U-001", payload={"purpose":"test"})
            with self.assertRaisesRegex(ValueError, "PM-DESIGN-001"):
                store.transition(entity_id=goal["id"], target="READY", actor_id="U-001", expected_revision=1)
            store.close()

    def test_review_approval_binds_reviewer_and_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_user(user_id="U-002", tenant_id="T-001", display_name="Reviewer", role="reviewer")
            store.add_member(project_id="P-001", user_id="U-002", role="reviewer")
            review = store.create_entity(entity_id="REV-001", entity_type="review", project_id="P-001", tenant_id="T-001", title="Architecture review", owner_id="U-001", payload={"reviewerId":"U-001", "reviewedRevision": 1, "decision":"APPROVED", "comments":"self"})
            store.transition(entity_id=review["id"], target="IN_REVIEW", actor_id="U-001", expected_revision=1)
            with self.assertRaisesRegex(ValueError, "PM-REVIEW-002"):
                store.transition(entity_id=review["id"], target="APPROVED", actor_id="U-001", expected_revision=2)
            store.update_entity_payload(entity_id=review["id"], payload={"reviewerId":"U-002", "reviewedRevision": 1, "decision":"APPROVED", "comments":"approved"}, actor_id="U-001", expected_revision=2)
            approved = store.transition(entity_id=review["id"], target="APPROVED", actor_id="U-002", expected_revision=3)
            self.assertEqual((approved["status"], approved["payload"]["reviewerId"]), ("APPROVED", "U-002"))
            store.close()

    def test_database_tree_and_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            tree = store.get_tree("P-001")
            self.assertEqual(len(tree), 10)
            node = store.add_node(project_id="P-001", node_id="NODE-001", name="Custom", parent_id=tree[0]["id"])
            self.assertEqual(node["parent_id"], tree[0]["id"])
            self.assertEqual(store.get_actor("U-001", "T-001")["role"], "owner")
            store.close()

    def test_project_members_are_tenant_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_user(user_id="U-002", tenant_id="T-001", display_name="Engineer", role="engineer")
            store.create_user(user_id="U-003", tenant_id="T-002", display_name="Other", role="engineer")
            self.assertEqual(store.add_member(project_id="P-001", user_id="U-002", role="engineer")["role"], "engineer")
            with self.assertRaises(PermissionError):
                store.add_member(project_id="P-001", user_id="U-003", role="engineer")
            self.assertEqual(len(store.list_members("P-001")), 2)
            store.close()

    def test_member_update_is_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_user(user_id="U-002", tenant_id="T-001", display_name="Engineer", role="engineer")
            store.add_member(project_id="P-001", user_id="U-002", role="engineer")
            self.assertTrue(any(row["action"] == "project.member.update" for row in store.list_audit("P-001")))
            store.close()

    def test_backlog_import_is_idempotent_and_preserves_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            items = json.loads((Path(__file__).parents[1] / "examples" / "implementation-backlog.json").read_text(encoding="utf-8"))
            self.assertEqual(store.import_backlog(project_id="P-001", items=items, actor_id="U-001"), 19)
            self.assertEqual(store.import_backlog(project_id="P-001", items=items, actor_id="U-001"), 0)
            backlog = store.list_backlog("P-001")
            self.assertEqual(len(backlog), 19)
            self.assertFalse(next(item for item in backlog if item["id"] == "PLC-001")["placeholder"])
            self.assertEqual(next(item for item in backlog if item["id"] == "PLC-001")["status"], "VALIDATED")
            self.assertEqual(store.reconcile_backlog(project_id="P-001", items=items, actor_id="U-001"), 19)
            self.assertTrue(any(item["message_type"] == "pm.backlog.reconciled" for item in store.list_events("P-001")))
            store.close()

    def test_sync_queue_requires_approval_for_push_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            with self.assertRaises(PermissionError):
                store.enqueue_sync(sync_id="SYNC-001", project_id="P-001", tenant_id="T-001", direction="PUSH_APPROVED", object_type="parameter", object_id="PAR-001", idempotency_key="idem-1", payload={})
            item = store.enqueue_sync(sync_id="SYNC-001", project_id="P-001", tenant_id="T-001", direction="PUSH_APPROVED", object_type="parameter", object_id="PAR-001", idempotency_key="idem-1", payload={"approvalId": "APR-001"})
            again = store.enqueue_sync(sync_id="SYNC-002", project_id="P-001", tenant_id="T-001", direction="PUSH_APPROVED", object_type="parameter", object_id="PAR-001", idempotency_key="idem-1", payload={"approvalId": "APR-001"})
            self.assertEqual(item["id"], again["id"])
            self.assertEqual(len(store.list_sync_queue("P-001")), 1)
            store.transition_sync("SYNC-001", "CONFLICT", "revision mismatch", actor_id="U-001")
            self.assertTrue(any(item["kind"] == "sync_conflict" for item in store.list_notifications("U-001", "P-001")))
            events = store.list_events("P-001")
            self.assertTrue(any(item["message_type"] == "pm.sync.queued" and item["payload"]["syncId"] == "SYNC-001" for item in events))
            self.assertTrue(any(item["message_type"] == "pm.sync.transitioned" and item["payload"]["to"] == "CONFLICT" for item in events))
            store.close()

    def test_traceability_search_and_sync_conflict_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_entity(entity_id="REQ-001", entity_type="requirement", project_id="P-001", tenant_id="T-001", title="Traceable requirement", owner_id="U-001")
            store.create_entity(entity_id="TC-001", entity_type="test_case", project_id="P-001", tenant_id="T-001", title="Trace test", owner_id="U-001")
            store.link_entities(project_id="P-001", from_id="REQ-001", to_id="TC-001", link_type="verified-by")
            self.assertEqual(len(store.search("P-001", "Traceable")), 1)
            self.assertEqual(store.list_links("P-001", "REQ-001")[0]["link_type"], "verified-by")
            store.enqueue_sync(sync_id="SYNC-001", project_id="P-001", tenant_id="T-001", direction="PULL_SNAPSHOT", object_type="artifact", object_id="ART-001", idempotency_key="pull-1", payload={})
            self.assertEqual(store.transition_sync("SYNC-001", "CONFLICT", "hash mismatch")["status"], "CONFLICT")
            store.close()

    def test_traceability_graph_resolves_payload_references_and_reports_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            evidence = store.create_entity(entity_id="EV-001", entity_type="evidence", project_id="P-001", tenant_id="T-001", title="Evidence", owner_id="U-001")
            release = store.create_entity(entity_id="REL-001", entity_type="release", project_id="P-001", tenant_id="T-001", title="Release", owner_id="U-001", payload={"evidenceLinks":[evidence["id"]], "artifactIds":["ART-MISSING"]})
            graph = store.traceability_graph("P-001")
            self.assertTrue(any(edge["from"] == "REL-001" and edge["to"] == "EV-001" for edge in graph["edges"]))
            self.assertEqual(graph["unresolvedReferences"][0]["reference"], "ART-MISSING")
            self.assertEqual(graph["freshness"], "CURRENT")
            store.close()

    def test_management_center_stats_notifications_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "pm.db"
            store = ProjectStore(db)
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_entity(entity_id="REQ-001", entity_type="requirement", project_id="P-001", tenant_id="T-001", title="MVP", owner_id="U-001")
            self.assertEqual(store.project_stats("P-001")["entities"]["requirement"]["DRAFT"], 1)
            self.assertEqual(store.notify(notification_id="N-001", project_id="P-001", recipient_id="U-001", kind="review", message="请评审" )["read"], 0)
            self.assertEqual(len(store.list_notifications("U-001")), 1)
            backup = Path(directory) / "backup.db"
            store.backup(str(backup))
            verification = store.verify_backup(str(backup), "P-001")
            self.assertTrue(verification["ready"])
            store.close()
            restored = ProjectStore(backup)
            self.assertEqual(restored.get_project("P-001")["name"], "Demo")
            restored.close()

    def test_control_plane_health_reports_scoped_operations_signals(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            health = store.control_plane_health("P-001")
            self.assertEqual((health["service"], health["search"]["freshness"], health["backup"]["status"], health["outbox"]["queued"]), ("zhinen-pm", "CURRENT", "AVAILABLE", 0))
            events = store.list_events("P-001")
            self.assertEqual((len(events), events[0]["message_type"], events[0]["status"], events[0]["schema_version"]), (1, "pm.project.created", "QUEUED", "0.1"))
            published = store.transition_event(events[0]["id"], "PUBLISHED", "U-001")
            self.assertEqual((published["status"], published["attempts"]), ("PUBLISHED", 1))
            self.assertTrue(health["deterministic"])
            store.close()

    def test_acceptance_report_summarizes_project_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_entity(entity_id="REL-001", entity_type="release", project_id="P-001", tenant_id="T-001", title="V0.1", owner_id="U-001")
            report = store.acceptance_report("P-001")
            self.assertEqual(report["summary"]["workPackages"], 0)
            self.assertEqual((report["summary"]["openIssues"], report["summary"]["closedIssues"]), (0, 0))
            self.assertFalse(report["releaseGates"][0]["ready"])
            self.assertGreaterEqual(report["auditCount"], 1)
            store.close()

    def test_notifications_can_be_read(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.notify(notification_id="N-001", project_id="P-001", recipient_id="U-001", kind="conflict", message="需处理同步冲突")
            self.assertEqual(store.mark_notification_read("N-001")["read"], 1)
            store.close()

    def test_machine_model_revision_snapshot_and_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="machine-engineering", owner_id="U-001")
            machine = store.create_machine_object(object_id="M-001", project_id="P-001", tenant_id="T-001", object_type="machine", name="Demo Machine", owner_id="U-001")
            store.create_machine_object(object_id="PLC-001", project_id="P-001", tenant_id="T-001", object_type="device", name="PLC", owner_id="U-001", parent_id="M-001", payload={"protocol": "TBD"})
            first = store.snapshot_machine(snapshot_id="S-001", project_id="P-001", machine_id="M-001", created_by="U-001")
            updated = store.update_machine_object(object_id="M-001", name=None, payload={"model": "v2"}, expected_revision=machine["revision"])
            self.assertEqual(updated["revision"], 2)
            events = store.list_events("P-001")
            self.assertTrue(any(item["message_type"] == "pm.machine_object.created" and item["payload"]["objectId"] == "M-001" for item in events))
            second = store.snapshot_machine(snapshot_id="S-002", project_id="P-001", machine_id="M-001", created_by="U-001")
            self.assertEqual(store.diff_snapshots(first["id"], second["id"])["changed"], ["M-001"])
            store.close()

    def test_machine_commit_binds_snapshot_and_tested_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="machine-engineering", owner_id="U-001")
            machine = store.create_machine_object(object_id="M-001", project_id="P-001", tenant_id="T-001", object_type="machine", name="Machine", owner_id="U-001")
            snapshot = store.snapshot_machine(snapshot_id="S-COMMIT", project_id="P-001", machine_id=machine["id"], created_by="U-001")
            artifact = store.create_artifact_manifest(artifact_id="ART-COMMIT", project_id="P-001", artifact_type="PLC", source_uri="inline://plc", content_hash="sha256:commit", artifact_revision="r1", toolchain_version="SIM", target_environment="SIMULATION", sensitivity="INTERNAL", owner_id="U-001")
            store.transition_artifact(artifact_id=artifact["id"], target="BUILT", actor_id="U-001")
            with self.assertRaisesRegex(RuntimeError, "artifact revision"):
                store.transition_artifact(artifact_id=artifact["id"], target="TESTED", actor_id="U-001", expected_revision=1)
            store.transition_artifact(artifact_id=artifact["id"], target="TESTED", actor_id="U-001")
            commit = store.create_machine_commit(commit_id="MC-001", project_id="P-001", tenant_id="T-001", machine_snapshot_id=snapshot["id"], artifact_ids=[artifact["id"]], branch="main", parent_commit_id=None, rollback_commit_id="MC-PREV", actor_id="U-001")
            self.assertEqual((commit["status"], commit["payload"]["machineSnapshotId"], commit["payload"]["components"][0]["id"]), ("BUILT", "S-COMMIT", "ART-COMMIT"))
            self.assertTrue(commit["payload"]["commitHash"].startswith("sha256:"))
            store.close()

    def test_machine_domain_objects_have_type_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="machine-engineering", owner_id="U-001")
            machine = store.create_machine_object(object_id="M-001", project_id="P-001", tenant_id="T-001", object_type="machine", name="Machine", owner_id="U-001")
            with self.assertRaisesRegex(ValueError, "tag missing"):
                store.create_machine_object(object_id="TAG-001", project_id="P-001", tenant_id="T-001", object_type="tag", name="Start", owner_id="U-001", parent_id=machine["id"], payload={})
            tag = store.create_machine_object(object_id="TAG-001", project_id="P-001", tenant_id="T-001", object_type="tag", name="Start", owner_id="U-001", parent_id=machine["id"], payload={"dataType": "BOOL", "access": "READ_ONLY"})
            self.assertEqual(tag["payload"]["dataType"], "BOOL")
            with self.assertRaisesRegex(ValueError, "severity"):
                store.create_machine_object(object_id="ALM-001", project_id="P-001", tenant_id="T-001", object_type="alarm", name="Door", owner_id="U-001", parent_id=machine["id"], payload={"severity": "S9"})
            store.close()

    def test_backlog_readiness_respects_dependencies_and_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            items = [{"id":"A-001","title":"A","area":"CORE","status":"VALIDATED","owner":"U-001","targetRelease":"V0.1","designGoal":"goal","acceptanceCriteria":["pass"],"testPlan":"test","rollbackPlan":"rollback"},{"id":"B-001","title":"B","area":"PLC","status":"PLACEHOLDER","placeholder":True,"owner":"U-001","targetRelease":"V0.2","dependencies":["A-001"],"designGoal":"goal","acceptanceCriteria":["pass"],"testPlan":"test","rollbackPlan":"rollback"}]
            store.import_backlog(project_id="P-001", items=items, actor_id="U-001")
            readiness = {item["id"]: item for item in store.backlog_readiness("P-001")}
            self.assertTrue(readiness["B-001"]["ready"])
            self.assertTrue(readiness["B-001"]["placeholder"])
            store.close()

    def test_engineering_capability_validation_is_deterministic_and_gated(self):
        self.assertEqual(len(list_capabilities()), 12)
        blocked = validate_capability("MOT-001", {"axis_simulation": True})
        self.assertEqual(blocked["result"], "BLOCKED")
        passed = validate_capability("MOT-001", {"axis_simulation": True, "limit_check": True, "state_machine": True})
        self.assertEqual(passed["result"], "CONTRACT_PASSED")
        self.assertEqual(passed["safetyGate"], "HUMAN_APPROVAL_REQUIRED")
        self.assertTrue(passed["validationHash"].startswith("sha256:"))
        self.assertEqual(validate_capability("ECO-001", {"consent": True, "scope": True, "retention": True})["result"], "CONTRACT_PASSED")
        self.assertEqual(simulation_evidence("PLC-001", {"source_present": True, "toolchain_pinned": True, "deterministic_build": True})["evidenceType"], "SIMULATION_RESULT")
        first = simulation_evidence("PLC-001", {"source_present": True, "toolchain_pinned": True, "deterministic_build": True})
        second = simulation_evidence("PLC-001", {"source_present": True, "toolchain_pinned": True, "deterministic_build": True})
        self.assertTrue(first["validationHash"].startswith("sha256:"))
        self.assertEqual(first["validationHash"], second["validationHash"])
        plc_error = simulation_evidence("PLC-001", {"source_present": True, "toolchain_pinned": True, "deterministic_build": True, "source": "syntax_error"})
        self.assertEqual((plc_error["result"], plc_error["diagnostic"]), ("FAILED", "compile"))
        hmi_error = simulation_evidence("HMI-001", {"tag_binding": True, "alarm_binding": True, "screen_smoke": True, "duplicate_tag": True})
        self.assertEqual((hmi_error["result"], hmi_error["diagnostic"]), ("FAILED", "binding"))
        build = build_plc_project("PROGRAM Main\nEND_PROGRAM", "PLC-SIM-1")
        self.assertEqual(build["result"], "PASSED")
        self.assertEqual(build["buildHash"], build_plc_project("PROGRAM Main\nEND_PROGRAM", "PLC-SIM-1")["buildHash"])
        self.assertIn("syntax_error", build_plc_project("SYNTAX_ERROR", "PLC-SIM-1")["errors"])
        self.assertEqual(simulate_plc_runtime()["result"], "PASSED")
        self.assertTrue(simulate_plc_runtime(injected_fault="watchdog")["safeStop"])
        self.assertEqual(simulate_plc_runtime(cycle_ms=60, watchdog_ms=50)["result"], "BLOCKED")
        firmware = build_firmware_image("bootloader\napplication", "FW-SIM-1", "EDGE", "sha256:previous", True)
        self.assertEqual((firmware["result"], firmware["powerRecovery"], firmware["deterministic"]), ("PASSED", "ROLLBACK_TO_PREVIOUS", True))
        self.assertIn("power_loss_without_previous_image", build_firmware_image("application", inject_power_loss=True)["errors"])
        self.assertIn("invalid_soft_limits", simulation_evidence("MOT-001", {"axis_simulation": True, "limit_check": True, "state_machine": True, "soft_limit_min": 10, "soft_limit_max": 1})["missing"])
        self.assertEqual(simulation_evidence("VIS-001", {"dataset_hash": True, "thresholds": True, "regression_set": True, "threshold_values": [0.5, 1.2]})["result"], "FAILED")
        self.assertEqual(simulation_evidence("LIFE-001", {"production_metrics": True, "quality_metrics": True, "maintenance_workflow": True})["result"], "PASSED")
        runtime_evidence = simulation_evidence("PLC-002", {"cycle_time": True, "watchdog": True, "safe_stop": True, "injected_fault": "watchdog"})
        self.assertEqual((runtime_evidence["diagnostic"], runtime_evidence["result"], runtime_evidence["runtime"]["safeStop"]), ("runtime", "FAILED", True))
        robot = simulation_evidence("ROB-001", {"handshake": True, "permission_scope": True, "fault_recovery": True, "handshake_sequence": ["INIT", "READY", "START", "DONE"]})
        self.assertEqual(robot["result"], "PASSED")
        self.assertEqual(robot["traceHash"], simulation_evidence("ROB-001", {"handshake": True, "permission_scope": True, "fault_recovery": True, "handshake_sequence": ["INIT", "READY", "START", "DONE"]})["traceHash"])
        self.assertIn("commissioning_checklist_incomplete", simulation_evidence("COMM-001", {"checklist": True, "evidence": True, "signoff": True, "checklist_items": [{"id": "FAT-1", "passed": False}]})["missing"])
        hmi = simulation_evidence("HMI-001", {"tag_binding": True, "alarm_binding": True, "screen_smoke": True, "tag_ids": ["Start", "Stop"], "bound_tag_ids": ["Start"]})
        self.assertIn("hmi_missing_tags:Stop", hmi["missing"])
        axis = simulate_motion_axis(0, 10, 2, -100, 100)
        self.assertEqual((axis["result"], axis["trajectory"][-1]), ("PASSED", 10.0))
        self.assertTrue(simulate_motion_axis(0, 101, 2, -100, 100)["safeStop"])
        vision = simulate_vision_algorithm([1, 0, 1, 0], [1, 0, 0, 0])
        self.assertEqual((vision["result"], vision["confusionMatrix"]["fn"], vision["accuracy"]), ("FAILED", 1, 0.75))
        edge = simulate_edge_replay(["E1", "E2", "E1"], True)
        self.assertEqual((edge["result"], edge["duplicates"], edge["applied"]), ("PASSED", 1, 2))
        self.assertEqual(simulate_edge_replay(["E1", "E1"], False)["result"], "FAILED")
        eda = simulate_eda_consistency(["DI-1", "DO-1"], ["DI-1", "DI-1"])
        self.assertEqual((eda["result"], eda["missing"], eda["duplicates"]), ("FAILED", ["DO-1"], ["DI-1"]))
        self.assertTrue(simulate_hmi_screens(["Home", "Alarm", "Recipe"], ["Home", "Recipe"])["missing"] == ["Alarm"])
        oee = simulate_oee_metrics(480, 60, 1000, 950, 20)
        self.assertEqual((oee["result"], oee["availability"], oee["quality"]), ("PASSED", 0.875, 0.95))
        self.assertEqual(simulate_oee_metrics(480, 500, 100, 100, 10)["result"], "BLOCKED")
        self.assertEqual(simulate_spc_metrics([10, 11, 10], 9, 12)["result"], "PASSED")
        self.assertEqual(simulate_spc_metrics([10, 13, 10], 9, 12)["outOfControl"], [1])
        self.assertEqual(simulate_health_check({"temperature": 50}, {"temperature": {"min": 0, "max": 80}})["result"], "PASSED")
        self.assertEqual(simulate_health_check({"temperature": 90}, {"temperature": {"min": 0, "max": 80}})["result"], "FAILED")
        self.assertEqual(simulate_health_check({"temperature": 50}, {"temperature": {}})["result"], "FAILED")
        lifecycle = simulation_evidence("LIFE-001", {"production_metrics": True, "quality_metrics": True, "maintenance_workflow": True, "spc_values": [10, 11, 10], "spc_lower": 9, "spc_upper": 12, "health_signals": {"temperature": 50}, "health_limits": {"temperature": {"min": 0, "max": 80}}})
        self.assertEqual((lifecycle["result"], lifecycle["spc"]["result"], lifecycle["health"]["result"]), ("PASSED", "PASSED", "PASSED"))
        matrix = validate_toolchain_matrix([{"id": "PLC-GOLDEN", "toolchain": "PLC-SIM-1", "compilePassed": True, "hmiSmoke": True, "expectedHash": "h1", "actualHash": "h1"}])
        self.assertEqual((matrix["result"], matrix["passed"], matrix["total"]), ("PASSED", 1, 1))

    def test_release_gate_requires_evidence_and_human_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            release = store.create_entity(entity_id="REL-001", entity_type="release", project_id="P-001", tenant_id="T-001", title="V0.1", owner_id="U-001", payload={})
            evidence = store.create_entity(entity_id="EV-001", entity_type="evidence", project_id="P-001", tenant_id="T-001", title="Smoke evidence", owner_id="U-001")
            store.link_entities(project_id="P-001", from_id=release["id"], to_id=evidence["id"], link_type="requires")
            self.assertFalse(store.release_gate("REL-001")["ready"])
            store.transition(entity_id="REL-001", target="CANDIDATE", actor_id="U-001", expected_revision=1)
            store.transition(entity_id="REL-001", target="VALIDATED", actor_id="U-001", expected_revision=2)
            store.transition(entity_id="REL-001", target="APPROVED", actor_id="U-001", expected_revision=3)
            with self.assertRaisesRegex(ValueError, "release gate"):
                store.transition(entity_id="REL-001", target="RELEASED", actor_id="U-001", expected_revision=4)
            store.transition(entity_id="EV-001", target="VALIDATED", actor_id="U-001", expected_revision=1)
            artifact = store.create_artifact_manifest(artifact_id="ART-REL-001", project_id="P-001", artifact_type="PLC", source_uri="inline://plc", content_hash="sha256:1234567890", artifact_revision="r1", toolchain_version="SIM", target_environment="SIMULATION", sensitivity="INTERNAL", owner_id="U-001")
            updated = store.get_entity("REL-001"); updated["payload"]["approvalId"] = "APR-001"; updated["payload"]["artifactIds"] = [artifact["id"]]; updated["payload"]["signature"] = "sig://REL-001"; updated["payload"]["sbom"] = "sbom://REL-001"; updated["payload"]["rollbackRevision"] = "REL-PREV-001"; updated["payload"].update({"sourceRevision":"git:demo@abc123", "machineProjectRevision":"v0.1.0", "schemaVersion":"0.1", "apiVersion":"0.1", "eventVersion":"0.1", "knownIssues":[], "targetEnvironment":"SIMULATION"})
            store.db.execute("UPDATE entities SET payload = ? WHERE id = ?", (json.dumps(updated["payload"], ensure_ascii=False), "REL-001")); store.db.commit()
            self.assertFalse(store.release_gate("REL-001")["ready"])
            store.transition_artifact(artifact_id=artifact["id"], target="BUILT", actor_id="U-001")
            store.transition_artifact(artifact_id=artifact["id"], target="TESTED", actor_id="U-001")
            composed = store.compose_release(release_id="REL-001", artifact_ids=[artifact["id"]], rollback_revision="REL-PREV-001", actor_id="U-001")
            self.assertTrue(composed["gate"]["ready"])
            self.assertTrue(composed["sbom"].startswith("sha256:"))
            coverage = store.capability_evidence("P-001", ["PLC-001", "HMI-001"])
            self.assertEqual(coverage, [{"capabilityId": "PLC-001", "validatedEvidence": [], "ready": False}, {"capabilityId": "HMI-001", "validatedEvidence": [], "ready": False}])
            self.assertEqual(store.transition(entity_id="REL-001", target="RELEASED", actor_id="U-001", expected_revision=store.get_entity("REL-001")["revision"])["status"], "RELEASED")
            store.close()

    def test_quality_closure_requires_evidence_and_regression_data(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            task = store.create_entity(entity_id="TASK-001", entity_type="work_item", project_id="P-001", tenant_id="T-001", title="Task", owner_id="U-001", payload={})
            for target, revision in (("IN_PROGRESS", 1), ("REVIEW", 2), ("TEST", 3)):
                store.transition(entity_id="TASK-001", target=target, actor_id="U-001", expected_revision=revision)
            with self.assertRaisesRegex(ValueError, "evidenceLinks"):
                store.transition(entity_id="TASK-001", target="DONE", actor_id="U-001", expected_revision=4)
            store.db.execute("UPDATE entities SET payload = ? WHERE id = ?", (json.dumps({"evidenceLinks": ["EV-001"]}), "TASK-001")); store.db.commit()
            self.assertEqual(store.transition(entity_id="TASK-001", target="DONE", actor_id="U-001", expected_revision=4)["status"], "DONE")
            issue = store.create_entity(entity_id="ISS-001", entity_type="issue", project_id="P-001", tenant_id="T-001", title="Issue", owner_id="U-001", payload={})
            for target, revision in (("REPRODUCED", 1), ("ROOT_CAUSED", 2), ("FIXED", 3), ("REGRESSION", 4)):
                store.transition(entity_id="ISS-001", target=target, actor_id="U-001", expected_revision=revision)
            with self.assertRaisesRegex(ValueError, "root cause"):
                store.transition(entity_id="ISS-001", target="CLOSED", actor_id="U-001", expected_revision=5)
            evidence = store.create_entity(entity_id="EV-ISS-001", entity_type="evidence", project_id="P-001", tenant_id="T-001", title="Issue regression", owner_id="U-001")
            store.transition(entity_id=evidence["id"], target="VALIDATED", actor_id="U-001", expected_revision=1)
            updated_issue = store.update_entity_payload(entity_id="ISS-001", actor_id="U-001", expected_revision=5, payload={"rootCause": "binding typo", "fixVersion": "V0.1.1", "regressionTestIds": ["TC-001"], "closureCriteria": ["retest passed"], "evidenceLinks": [evidence["id"]]})
            self.assertEqual(store.transition(entity_id="ISS-001", target="CLOSED", actor_id="U-001", expected_revision=updated_issue["revision"])["status"], "CLOSED")
            snapshot = store.create_entity(entity_id="PAR-001", entity_type="parameter_snapshot", project_id="P-001", tenant_id="T-001", title="Speed", owner_id="U-001", payload={"speed": 100})
            approved = store.transition(entity_id=snapshot["id"], target="VALIDATED", actor_id="U-001", expected_revision=1)
            approved = store.transition(entity_id=approved["id"], target="APPROVED", actor_id="U-001", expected_revision=2)
            with self.assertRaisesRegex(ValueError, "apply endpoint"):
                store.transition(entity_id=approved["id"], target="APPLIED", actor_id="U-001", expected_revision=3)
            applied = store.apply_parameter_snapshot(snapshot_id=approved["id"], sync_id="SYNC-PAR-001", approval_id="APR-PAR-001", actor_id="U-001")
            self.assertEqual((applied["snapshot"]["status"], applied["sync"]["direction"], applied["sync"]["payload"]["approvalId"]), ("APPLIED", "PUSH_APPROVED", "APR-PAR-001"))
            store.close()

    def test_test_case_execution_generates_validated_evidence_and_release_link(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            case = store.create_entity(entity_id="TC-001", entity_type="test_case", project_id="P-001", tenant_id="T-001", title="Smoke", owner_id="U-001", payload={"steps": ["run"], "inputs": {"mode": "smoke"}, "expected": {"result": "pass"}, "thresholds": {"maxMs": 100}})
            release = store.create_entity(entity_id="REL-001", entity_type="release", project_id="P-001", tenant_id="T-001", title="V0.1", owner_id="U-001")
            result = store.execute_test_case(project_id="P-001", tenant_id="T-001", test_case_id=case["id"], run_id="RUN-001", evidence_id="EV-001", actor_id="U-001", passed=True, release_id=release["id"])
            self.assertEqual(result["testRun"]["status"], "PASSED")
            self.assertEqual(result["evidence"]["status"], "VALIDATED")
            self.assertEqual((result["testRun"]["payload"]["environment"], result["evidence"]["payload"]["testCaseRevision"], result["evidence"]["payload"]["executedBy"]), ("SIMULATION", 1, "U-001"))
            self.assertEqual(store.list_links("P-001", "REL-001")[0]["to_id"], "EV-001")
            store.close()

    def test_knowledge_approval_requires_verified_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            article = store.create_entity(entity_id="KB-TEST", entity_type="knowledge", project_id="P-001", tenant_id="T-001", title="Validated guidance", owner_id="U-001", payload={})
            store.transition(entity_id=article["id"], target="REVIEW", actor_id="U-001", expected_revision=1)
            store.transition(entity_id=article["id"], target="VALIDATED", actor_id="U-001", expected_revision=2)
            with self.assertRaisesRegex(ValueError, "source"):
                store.transition(entity_id=article["id"], target="APPROVED", actor_id="U-001", expected_revision=3)
            updated = store.update_entity_payload(entity_id=article["id"], actor_id="U-001", expected_revision=3, payload={"source": "QA-REVIEW-001", "applicableVersion": "V0.1", "validationStatus": "VALIDATED", "testIds": ["TC-001"], "expiryCondition": "toolchain changes"})
            self.assertEqual(store.transition(entity_id=article["id"], target="APPROVED", actor_id="U-001", expected_revision=updated["revision"])["status"], "APPROVED")
            store.close()

    def test_maintenance_completion_requires_field_record(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            record = store.create_entity(entity_id="MAINT-001", entity_type="maintenance", project_id="P-001", tenant_id="T-001", title="Firmware update", owner_id="U-001", payload={})
            store.transition(entity_id=record["id"], target="IN_PROGRESS", actor_id="U-001", expected_revision=1)
            with self.assertRaisesRegex(ValueError, "machine"):
                store.transition(entity_id=record["id"], target="COMPLETED", actor_id="U-001", expected_revision=2)
            updated = store.update_entity_payload(entity_id=record["id"], actor_id="U-001", expected_revision=2, payload={"machineId": "MACHINE-001", "executorId": "U-001", "releaseId": "REL-001", "result": "PASS", "exceptions": [], "rollback": {"available": True, "revision": "REL-PREV-001"}})
            self.assertEqual(store.transition(entity_id=record["id"], target="COMPLETED", actor_id="U-001", expected_revision=updated["revision"])["status"], "COMPLETED")
            store.close()

    def test_deployment_request_rejects_missing_release_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            deployment = store.create_entity(entity_id="DEP-001", entity_type="deployment", project_id="P-001", tenant_id="T-001", title="Deploy V0.1", owner_id="U-001", payload={})
            with self.assertRaisesRegex(ValueError, "authorization needs release"):
                store.transition(entity_id=deployment["id"], target="AUTHORIZED", actor_id="U-001", expected_revision=1)
            store.close()

    def test_critical_issue_triggers_escalation_notification(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            issue = store.create_entity(entity_id="ISS-S0", entity_type="issue", project_id="P-001", tenant_id="T-001", title="Safety trip", owner_id="U-001", payload={"severity": "S0"})
            self.assertEqual(issue["payload"]["severity"], "S0")
            alerts = store.list_notifications("U-001", "P-001")
            self.assertEqual((len(alerts), alerts[0]["kind"]), (1, "issue_escalation"))
            store.close()

    def test_failed_test_case_execution_retains_draft_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            case = store.create_entity(entity_id="TC-FAIL", entity_type="test_case", project_id="P-001", tenant_id="T-001", title="Failure", owner_id="U-001", payload={"steps": ["run"], "inputs": {"mode": "failure"}, "expected": {"result": "pass"}, "thresholds": {"maxMs": 100}})
            result = store.execute_test_case(project_id="P-001", tenant_id="T-001", test_case_id=case["id"], run_id="RUN-FAIL", evidence_id="EV-FAIL", actor_id="U-001", passed=False)
            self.assertEqual(result["testRun"]["status"], "FAILED")
            self.assertEqual(result["evidence"]["status"], "DRAFT")
            self.assertEqual(result["evidence"]["payload"]["result"], "FAILED")
            self.assertEqual((result["issue"]["status"], result["issue"]["payload"]["evidenceLinks"]), ("OPEN", ["EV-FAIL"]))
            self.assertEqual(store.list_links("P-001", "ISSUE-RUN-FAIL")[0]["link_type"], "diagnosed_by")
            self.assertEqual(store.list_links("P-001", "TC-FAIL")[0]["to_id"], "EV-FAIL")
            store.close()

    def test_test_plan_batch_execution_aggregates_results(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            first = store.create_entity(entity_id="TC-PLAN-1", entity_type="test_case", project_id="P-001", tenant_id="T-001", title="First", owner_id="U-001", payload={"steps": ["run"], "inputs": {"case": 1}, "expected": {"result": "pass"}, "thresholds": {"maxMs": 100}})
            second = store.create_entity(entity_id="TC-PLAN-2", entity_type="test_case", project_id="P-001", tenant_id="T-001", title="Second", owner_id="U-001", payload={"steps": ["run"], "inputs": {"case": 2}, "expected": {"result": "pass"}, "thresholds": {"maxMs": 100}})
            plan = store.create_entity(entity_id="TP-001", entity_type="test_plan", project_id="P-001", tenant_id="T-001", title="Acceptance", owner_id="U-001", payload={"testCaseIds": [first["id"], second["id"]]})
            result = store.execute_test_plan(project_id="P-001", tenant_id="T-001", test_plan_id=plan["id"], actor_id="U-001", run_prefix="TP-RUN", evidence_prefix="TP-EV", passed_by_case={second["id"]: False})
            self.assertEqual((result["testPlan"]["status"], result["summary"]), ("FAILED", {"total": 2, "passed": 1, "failed": 1}))
            self.assertEqual(result["results"][1]["evidence"]["status"], "DRAFT")
            store.close()

    def test_ai_context_is_minimal_and_denies_cross_project(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            store.create_entity(entity_id="REQ-001", entity_type="requirement", project_id="P-001", tenant_id="T-001", title="Scoped", owner_id="U-001")
            context = build_context(store, project_id="P-001", object_ids=["REQ-001"], actor_id="AI-001")
            self.assertEqual(len(context["objects"]), 1)
            self.assertNotIn("DEPLOY", context["allowedActions"])
            with self.assertRaises(ValueError):
                build_context(store, project_id="P-001", object_ids=["REQ-001"] * 21, actor_id="AI-001")
            store.close()

    def test_ai_context_excludes_unvalidated_operational_records(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            draft_evidence = store.create_entity(entity_id="EV-DRAFT-AI", entity_type="evidence", project_id="P-001", tenant_id="T-001", title="Draft evidence", owner_id="U-001")
            approved_knowledge = store.create_entity(entity_id="KB-APPROVED-AI", entity_type="knowledge", project_id="P-001", tenant_id="T-001", title="Approved knowledge", owner_id="U-001", payload={"source": "QA", "applicableVersion": "V0.1", "validationStatus": "VALIDATED", "testIds": ["TC-1"], "expiryCondition": "new release"})
            store.transition(entity_id=approved_knowledge["id"], target="REVIEW", actor_id="U-001", expected_revision=1)
            store.transition(entity_id=approved_knowledge["id"], target="VALIDATED", actor_id="U-001", expected_revision=2)
            store.transition(entity_id=approved_knowledge["id"], target="APPROVED", actor_id="U-001", expected_revision=3)
            context = build_context(store, project_id="P-001", object_ids=[draft_evidence["id"], approved_knowledge["id"]], actor_id="AI-001")
            self.assertEqual([item["id"] for item in context["objects"]], ["KB-APPROVED-AI"])
            self.assertEqual(context["omitted"][0]["id"], "EV-DRAFT-AI")
            store.close()

    def test_ai_context_excludes_unconfirmed_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            deployment = store.create_entity(entity_id="DEP-AI", entity_type="deployment", project_id="P-001", tenant_id="T-001", title="Pending deployment", owner_id="U-001")
            context = build_context(store, project_id="P-001", object_ids=[deployment["id"]], actor_id="AI-001")
            self.assertEqual(context["objects"], [])
            self.assertEqual(context["omitted"][0]["id"], "DEP-AI")
            store.close()

    def test_ai_context_http_route_requires_project_read_scope_and_audits_access(self):
        with tempfile.TemporaryDirectory() as directory:
            server = create_server(str(Path(directory) / "pm.db"), port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def call(path, payload=None):
                data = json.dumps(payload).encode() if payload is not None else None
                req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}{path}", data=data, headers={"Content-Type": "application/json", "X-Actor-Id": "U-001", "X-Tenant-Id": "T-001"}, method="POST" if payload is not None else "GET")
                with urllib.request.urlopen(req) as response:
                    return response.status, json.loads(response.read())
            call("/api/projects", {"projectId": "P-001", "tenantId": "T-001", "name": "Demo", "ownerId": "U-001"})
            status, context = call("/api/ai/context", {"projectId": "P-001", "tenantId": "T-001", "actorId": "U-001", "objectIds": []})
            self.assertEqual((status, context["projectId"]), (200, "P-001"))
            _, audit = call("/api/projects/P-001/audit")
            self.assertTrue(any(item["action"] == "ai.context.read" for item in audit["audit"]))
            with self.assertRaises(urllib.error.HTTPError):
                call("/api/ai/context", {"projectId": "P-001", "tenantId": "T-001", "actorId": "UNKNOWN", "objectIds": []})
            _, audit_after_denial = call("/api/projects/P-001/audit")
            self.assertTrue(any(item["action"] == "authorization.denied" and item["outcome"] == "denied" for item in audit_after_denial["audit"]))
            server.shutdown(); server.server_close()

    def test_project_discovery_is_tenant_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            server = create_server(str(Path(directory) / "pm.db"), port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def get_projects(headers):
                req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/projects", headers=headers)
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read())
            def post_project(project):
                req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/projects", data=json.dumps(project).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req) as response:
                    return response.status
            post_project({"projectId": "P-001", "tenantId": "T-001", "name": "One", "ownerId": "U-001"})
            post_project({"projectId": "P-002", "tenantId": "T-002", "name": "Two", "ownerId": "U-002"})
            scoped = get_projects({"X-Actor-Id": "U-001", "X-Tenant-Id": "T-001"})
            self.assertEqual([item["id"] for item in scoped["projects"]], ["P-001"])
            with self.assertRaises(urllib.error.HTTPError):
                get_projects({})
            server.shutdown(); server.server_close()

    def test_artifact_manifest_requires_hash_and_preserves_engineering_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            with self.assertRaises(ValueError):
                store.create_artifact_manifest(artifact_id="ART-001", project_id="P-001", artifact_type="FIRMWARE", source_uri="edge://fw", content_hash="x", artifact_revision="1", toolchain_version="TBD", target_environment="EDGE", sensitivity="EDGE_ONLY", owner_id="U-001")
            item = store.create_artifact_manifest(artifact_id="ART-001", project_id="P-001", artifact_type="FIRMWARE", source_uri="edge://fw", content_hash="sha256:1234567890", artifact_revision="1", toolchain_version="GCC-TBD", target_environment="EDGE", sensitivity="EDGE_ONLY", owner_id="U-001")
            self.assertEqual((item["artifact_type"], item["sensitivity"]), ("FIRMWARE", "EDGE_ONLY"))
            store.close()

    def test_plc_download_and_monitor_are_gated_and_deterministic(self):
        ready = simulate_plc_download(artifact_id="ART-PLC", artifact_hash="sha256:abc12345", artifact_status="APPROVED", target_machine_id="M-001", approval_id="APR-001", rollback_revision="MC-000")
        self.assertEqual((ready["result"], ready["writesController"], ready["humanApprovalRequired"]), ("READY_FOR_EDGE", False, True))
        self.assertEqual(ready["transferHash"], simulate_plc_download(artifact_id="ART-PLC", artifact_hash="sha256:abc12345", artifact_status="APPROVED", target_machine_id="M-001", approval_id="APR-001", rollback_revision="MC-000")["transferHash"])
        blocked = simulate_plc_download(artifact_id="ART-PLC", artifact_hash="sha256:abc12345", artifact_status="TESTED", target_machine_id="M-001", approval_id=None, rollback_revision=None)
        self.assertEqual(blocked["result"], "BLOCKED")
        monitor = simulate_plc_monitor(tags={"Run": True, "Speed": 10}, cycles=5)
        self.assertEqual((monitor["result"], [item["name"] for item in monitor["tags"]]), ("PASSED", ["Run", "Speed"]))
        faulted = simulate_plc_monitor(tags={"Run": True}, cycles=5, fault="safety_trip")
        self.assertEqual((faulted["result"], faulted["safeStop"], faulted["tags"][0]["quality"]), ("FAILED", True, "BAD"))

    def test_product_trace_is_complete_and_deterministic(self):
        trace = {"productId": "PRODUCT-001", "machineId": "M-001", "recipeId": "RECIPE-001", "plcState": "DONE", "measurement": {"length": 10.2}, "parameters": {"speed": 100}, "timestamp": "2026-09-10T00:00:00Z"}
        first = simulate_product_trace(trace)
        second = simulate_product_trace(trace)
        self.assertEqual((first["result"], first["traceHash"]), ("PASSED", second["traceHash"]))
        self.assertEqual(simulate_product_trace({"productId": "PRODUCT-001"})["result"], "BLOCKED")
        self.assertEqual(simulation_evidence("LIFE-001", {"production_metrics": True, "quality_metrics": True, "maintenance_workflow": True, "product_trace": trace})["productTrace"]["result"], "PASSED")

    def test_ecosystem_contract_is_deterministic_and_denies_control_authority(self):
        package = {"packageId": "PKG-001", "version": "1.0.0", "provider": "zhinen", "consent": True, "scope": ["aggregated_oee"], "retentionDays": 90, "signature": "sha256:package", "permissions": ["read_metrics"]}
        first = simulate_ecosystem_contract(package)
        second = simulate_ecosystem_contract(package)
        self.assertEqual((first["result"], first["contractHash"]), ("PASSED", second["contractHash"]))
        self.assertFalse(first["directControlAllowed"])
        blocked = simulate_ecosystem_contract({**package, "permissions": ["direct_deploy"]})
        self.assertIn("forbidden_permission:direct_deploy", blocked["errors"])
        self.assertEqual(simulation_evidence("ECO-001", {"consent": True, "scope": True, "retention": True, "package": package})["ecosystem"]["result"], "PASSED")

    def test_commissioning_fat_sat_order_and_evidence_are_gated(self):
        sequence = ["24V", "Network", "EtherCAT", "IO", "Safety", "Servo", "Cylinder", "Vision", "Station", "Auto Cycle", "Burn-in"]
        items = [{"id": step, "passed": True} for step in sequence]
        self.assertEqual(simulate_commissioning_checklist(sequence, items)["result"], "PASSED")
        self.assertEqual(simulate_commissioning_checklist(list(reversed(sequence)), items)["reason"], "commissioning_sequence_invalid")
        self.assertEqual(simulate_commissioning_checklist(sequence, items[:-1])["reason"], "commissioning_evidence_incomplete")
        self.assertEqual(simulation_evidence("COMM-001", {"checklist": True, "evidence": True, "signoff": True, "checklist_sequence": sequence, "checklist_items": items})["commissioning"]["result"], "PASSED")

    def test_http_api_project_tree_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            server = create_server(str(Path(directory) / "pm.db"), port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(path, payload=None):
                    data = json.dumps(payload).encode() if payload is not None else None
                    req = urllib.request.Request(f"http://127.0.0.1:8765{path}", data=data, headers={"Content-Type": "application/json", "X-Actor-Id": "U-001", "X-Tenant-Id": "T-001"}, method="POST" if payload is not None else "GET")
                    req = urllib.request.Request(req.full_url.replace("8765", str(server.server_port)), data=req.data, headers=dict(req.header_items()), method=req.method)
                    with urllib.request.urlopen(req) as response:
                        return response.status, json.loads(response.read())
                status, _ = request("/api/projects", {"projectId": "P-001", "tenantId": "T-001", "name": "Demo", "ownerId": "U-001"})
                self.assertEqual(status, 201)
                status, entity = request("/api/projects/P-001/entities", {"id": "REQ-001", "type": "requirement", "tenantId": "T-001", "title": "MVP", "ownerId": "U-001", "actorId": "U-001", "payload": {"description": "MVP contract", "priority": "P0", "acceptanceCriteria": ["pass"], "nonGoals": ["field control"], "source": "product", "traceLinks": ["MASTER_PLAN.md"]}})
                self.assertEqual(status, 201)
                status, updated = request("/api/entities/REQ-001/transition", {"target": "READY", "actorId": "U-001", "tenantId": "T-001", "expectedRevision": entity["revision"]})
                self.assertEqual((status, updated["status"]), (200, "READY"))
                status, build = request("/api/projects/P-001/builds/plc", {"actorId": "U-001", "tenantId": "T-001", "artifactId": "ART-PLC-001", "source": "PROGRAM Main\nEND_PROGRAM", "toolchainVersion": "PLC-SIM-1"})
                self.assertEqual((status, build["build"]["result"]), (201, "PASSED"))
                self.assertEqual((build["artifact"]["status"], build["testRun"]["status"], build["evidence"]["status"], build["evidence"]["payload"]["capabilityId"]), ("TESTED", "PASSED", "VALIDATED", "PLC-001"))
                status, approved_plc = request("/api/artifacts/ART-PLC-001/transition", {"target": "APPROVED", "actorId": "U-001", "tenantId": "T-001"})
                self.assertEqual((status, approved_plc["status"]), (200, "APPROVED"))
                status, download = request("/api/projects/P-001/plc/download-simulate", {"actorId": "U-001", "tenantId": "T-001", "artifactId": "ART-PLC-001", "targetMachineId": "M-001", "approvalId": "APR-PLC-001", "rollbackRevision": "MC-PREV-001"})
                self.assertEqual((status, download["result"], download["writesController"]), (200, "READY_FOR_EDGE", False))
                status, monitor = request("/api/projects/P-001/plc/monitor-simulate", {"actorId": "U-001", "tenantId": "T-001", "tags": {"Run": True, "Speed": 10}, "cycles": 5})
                self.assertEqual((status, monitor["result"], [item["name"] for item in monitor["tags"]]), (200, "PASSED", ["Run", "Speed"]))
                status, failed_build = request("/api/projects/P-001/builds/plc", {"actorId": "U-001", "tenantId": "T-001", "artifactId": "ART-PLC-FAIL", "testRunId": "RUN-PLC-FAIL", "evidenceId": "EV-PLC-FAIL", "source": "PROGRAM Main\nSYNTAX_ERROR", "toolchainVersion": "PLC-SIM-1"})
                self.assertEqual((status, failed_build["build"]["result"], failed_build["issue"]["title"], failed_build["issue"]["payload"]["capabilityId"]), (201, "FAILED", "PLC build failed", "PLC-001"))
                self.assertEqual(failed_build["evidence"]["status"], "DRAFT")
                status, build_notifications = request("/api/notifications?recipientId=U-001&projectId=P-001")
                self.assertTrue(any(item["kind"] == "build_failed" for item in build_notifications["notifications"]))
                status, events = request("/api/projects/P-001/events")
                self.assertTrue(any(item["message_type"] == "pm.artifact.created" and item["payload"].get("artifactId") == "ART-PLC-FAIL" for item in events["events"]))
                status, matrix = request("/api/projects/P-001/toolchain-matrix", {"actorId": "U-001", "tenantId": "T-001", "validationId": "TV-PLC-001", "cases": [{"id": "PLC-GOLDEN", "toolchain": "PLC-SIM-1", "compilePassed": True, "hmiSmoke": True, "expectedHash": "h1", "actualHash": "h1"}]})
                self.assertEqual((status, matrix["validation"]["status"], matrix["matrix"]["result"]), (201, "VALIDATED", "PASSED"))
                status, simulation = request("/api/projects/P-001/simulate", {"actorId": "U-001", "tenantId": "T-001", "capabilityId": "HMI-001", "testRunId": "RUN-HMI-001", "evidenceId": "EV-HMI-001", "payload": {"tag_binding": True, "alarm_binding": True, "screen_smoke": True, "duplicate_tag": True}})
                self.assertEqual((status, simulation["validation"]["result"], simulation["testRun"]["status"], simulation["evidence"]["status"], simulation["issue"]["status"]), (201, "FAILED", "FAILED", "DRAFT", "OPEN"))
                status, notifications = request("/api/notifications?recipientId=U-001&projectId=P-001")
                self.assertTrue(any(item["kind"] == "test_failed" for item in notifications["notifications"]))
                status, issue_links = request("/api/projects/P-001/links?entityId=" + simulation["issue"]["id"])
                self.assertEqual((status, issue_links["links"][0]["to_id"], issue_links["links"][0]["link_type"]), (200, simulation["evidence"]["id"], "diagnosed_by"))
                status, tree = request("/api/projects/P-001/tree")
                self.assertEqual((status, len(tree["tree"])), (200, 10))
                items = [{"id": "PM-001", "title": "Control Center", "area": "PM", "status": "IMPLEMENTING", "owner": "U-001", "targetRelease": "V0.1", "designGoal": "可追踪", "acceptanceCriteria": ["可查询"], "testPlan": "API smoke", "rollbackPlan": "保留旧版本", "placeholder": False}]
                status, result = request("/api/projects/P-001/backlog/import", {"actorId": "U-001", "tenantId": "T-001", "items": items})
                self.assertEqual((status, result["inserted"]), (201, 1))
                status, backlog = request("/api/projects/P-001/backlog")
                self.assertEqual((status, backlog["items"][0]["id"]), (200, "PM-001"))
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
