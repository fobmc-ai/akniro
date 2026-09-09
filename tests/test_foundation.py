import json
import sys
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_foundation.audit import AuditLog
from zhinen_foundation.envelope import make_message
from zhinen_foundation.project import ProjectValidationError, load_project, validate_project
from zhinen_foundation.registry import Capability, CapabilityRegistry
from zhinen_foundation.resources import ResourceLease, ResourceLeaseManager
from zhinen_foundation.store import ProjectStore, RevisionConflictError
from zhinen_foundation.migration import MigrationError, MigrationRegistry
from zhinen_foundation.outbox import Outbox
from zhinen_foundation.service import ProjectService, ServiceError
from zhinen_foundation.durable_outbox import DurableOutbox


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

    def test_revision_round_trip_and_immutability(self):
        project = json.loads((ROOT / "examples" / "machine-project.valid.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(directory)
            path = store.save(project)
            self.assertEqual(store.load("v0.1.0"), project)
            self.assertEqual(path.name, "v0.1.0.json")
            altered = dict(project, name="must not overwrite")
            with self.assertRaises(RevisionConflictError):
                store.save(altered)


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

    def test_migration_is_ordered_and_updates_version(self):
        registry = MigrationRegistry()
        registry.register("0.0", "0.1", lambda value: dict(value, schemaVersion="0.1"))
        migrated = registry.migrate({"schemaVersion": "0.0", "projectId": "ZN-001"}, "0.1")
        self.assertEqual(migrated["schemaVersion"], "0.1")
        with self.assertRaises(MigrationError):
            registry.migrate({"schemaVersion": "0.2"}, "0.1")

    def test_outbox_retries_failed_publish(self):
        message = make_message("event", "test.created", {}, actor="test", tenant_id="T", site_id="S", machine_id="M")
        outbox = Outbox()
        outbox.append(message)
        attempts = []
        def publisher(item):
            attempts.append(item.messageId)
            if len(attempts) == 1:
                raise RuntimeError("temporary")
        self.assertEqual(outbox.publish_pending(publisher), 0)
        self.assertEqual(outbox.publish_pending(publisher), 1)
        self.assertEqual(len(attempts), 2)

    def test_project_service_persists_audits_and_event(self):
        project = json.loads((ROOT / "examples" / "machine-project.valid.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            service = ProjectService(ProjectStore(directory), AuditLog(), Outbox())
            path = service.save_revision(project, actor="codex", tenant_id="T", site_id="S", machine_id="M")
            self.assertTrue(Path(path).exists())
            self.assertEqual(len(service.audit.all()), 1)
            self.assertEqual(len(service.outbox.pending()), 1)

    def test_durable_outbox_survives_restart_and_retries(self):
        message = make_message("event", "project.created", {}, actor="service", tenant_id="T", site_id="S", machine_id="M")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "control-plane.db"
            first = DurableOutbox(database)
            first.append(message)
            first.close()
            second = DurableOutbox(database)
            attempts = []
            def publisher(item):
                attempts.append(item["messageId"])
                if len(attempts) == 1:
                    raise RuntimeError("broker unavailable")
            self.assertEqual(second.publish_pending(publisher), 0)
            second.close()
            third = DurableOutbox(database)
            self.assertEqual(third.publish_pending(publisher), 1)
            self.assertEqual(attempts, [message.messageId, message.messageId])
            self.assertEqual(third.pending(), [])
            third.close()


if __name__ == "__main__":
    unittest.main()
