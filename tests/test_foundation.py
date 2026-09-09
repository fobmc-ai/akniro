import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_foundation.audit import AuditLog
from zhinen_foundation.envelope import make_message
from zhinen_foundation.project import ProjectValidationError, load_project, validate_project
from zhinen_foundation.registry import Capability, CapabilityRegistry
from zhinen_foundation.resources import ResourceLease, ResourceLeaseManager


ROOT = Path(__file__).parents[1]


class ProjectContractTests(unittest.TestCase):
    def test_valid_example_loads(self):
        project = load_project(ROOT / "examples" / "machine-project.valid.json")
        self.assertEqual(project["schemaVersion"], "0.1")

    def test_unknown_field_is_rejected(self):
        project = json.loads((ROOT / "examples" / "machine-project.valid.json").read_text())
        project["unexpected"] = True
        with self.assertRaisesRegex(ProjectValidationError, r"unknown fields"):
            validate_project(project)

    def test_duplicate_component_is_rejected(self):
        project = json.loads((ROOT / "examples" / "machine-project.valid.json").read_text())
        project["components"].append(project["components"][0])
        with self.assertRaisesRegex(ProjectValidationError, r"duplicate component ID"):
            validate_project(project)


class CoordinationContractTests(unittest.TestCase):
    def test_capability_prerequisite_and_lifecycle(self):
        registry = CapabilityRegistry()
        registry.register(Capability("core.base", "0.1.0", "stable", "core"))
        registry.register(Capability("plc.runtime", "0.1.0", "experimental", "core", ("core.base",)))
        self.assertTrue(registry.can_activate("plc.runtime"))

    def test_exclusive_lease_conflict_and_expiry(self):
        manager = ResourceLeaseManager()
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        manager.acquire(ResourceLease("LEASE-001", "fieldbus-0", "PLC", "realtime", "exclusive", now + timedelta(minutes=1)), now=now)
        with self.assertRaisesRegex(RuntimeError, r"resource unavailable"):
            manager.acquire(ResourceLease("LEASE-002", "fieldbus-0", "AI", "background", "shared", now + timedelta(minutes=1)), now=now)
        manager.expire(now + timedelta(minutes=1))
        self.assertEqual(manager.active(), ())

    def test_message_envelope_has_coordination_metadata(self):
        message = make_message("event", "project.revision.created", {"revision": "v0.1.0"}, actor="system", tenant_id="TENANT-001", site_id="SITE-001", machine_id="MACHINE-001")
        data = message.as_dict()
        self.assertEqual(data["kind"], "event")
        self.assertTrue(data["messageId"] and data["correlationId"] and data["idempotencyKey"])

    def test_audit_log_is_append_only(self):
        log = AuditLog()
        record = log.append(action="project.validate", actor="codex", target="ZN-MACHINE-DEMO", outcome="success", correlation_id="CORR-001")
        self.assertEqual(len(log.all()), 1)
        self.assertEqual(log.as_dicts()[0]["audit_id"], record.audit_id)


if __name__ == "__main__":
    unittest.main()
