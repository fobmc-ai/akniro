import sys
import tempfile
import unittest
import urllib.request
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_pm.authorization import Actor, AuthorizationError, authorize
from zhinen_pm.state_machine import InvalidTransition, assert_transition
from zhinen_pm.store import ProjectStore
from zhinen_pm.server import create_server
import threading


class PM0Tests(unittest.TestCase):
    def test_state_machine_rejects_skipping_test(self):
        with self.assertRaises(InvalidTransition):
            assert_transition("work_item", "IN_PROGRESS", "DONE")

    def test_ai_cannot_deploy(self):
        with self.assertRaises(AuthorizationError):
            authorize(Actor("AI-001", "ai", "T-001", frozenset({"P-001"})), "DEPLOY", tenant_id="T-001", project_id="P-001")

    def test_store_scope_revision_transition_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            entity = store.create_entity(entity_id="REQ-001", entity_type="requirement", project_id="P-001", tenant_id="T-001", title="Define MVP", owner_id="U-001")
            self.assertEqual(entity["status"], "DRAFT")
            updated = store.transition(entity_id="REQ-001", target="READY", actor_id="U-001", expected_revision=1)
            self.assertEqual(updated["revision"], 2)
            with self.assertRaisesRegex(RuntimeError, "revision conflict"):
                store.transition(entity_id="REQ-001", target="IMPLEMENTING", actor_id="U-001", expected_revision=1)
            self.assertGreaterEqual(len(store.audit("P-001")), 2)
            store.close()

    def test_database_tree_and_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory) / "pm.db")
            store.create_project(project_id="P-001", tenant_id="T-001", name="Demo", kind="platform", owner_id="U-001")
            tree = store.get_tree("P-001")
            self.assertEqual(len(tree), 9)
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

    def test_http_api_project_tree_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            server = create_server(str(Path(directory) / "pm.db"), port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(path, payload=None):
                    data = json.dumps(payload).encode() if payload is not None else None
                    req = urllib.request.Request(f"http://127.0.0.1:8765{path}", data=data, headers={"Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
                    req = urllib.request.Request(req.full_url.replace("8765", str(server.server_port)), data=req.data, headers=dict(req.header_items()), method=req.method)
                    with urllib.request.urlopen(req) as response:
                        return response.status, json.loads(response.read())
                status, _ = request("/api/projects", {"projectId": "P-001", "tenantId": "T-001", "name": "Demo", "ownerId": "U-001"})
                self.assertEqual(status, 201)
                status, entity = request("/api/projects/P-001/entities", {"id": "REQ-001", "type": "requirement", "tenantId": "T-001", "title": "MVP", "ownerId": "U-001", "actorId": "U-001"})
                self.assertEqual(status, 201)
                status, updated = request("/api/entities/REQ-001/transition", {"target": "READY", "actorId": "U-001", "tenantId": "T-001", "expectedRevision": entity["revision"]})
                self.assertEqual((status, updated["status"]), (200, "READY"))
                status, tree = request("/api/projects/P-001/tree")
                self.assertEqual((status, len(tree["tree"])), (200, 9))
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
