from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .store import ProjectStore
from .authorization import Actor, authorize
from .engineering import list_capabilities, validate_capability, simulation_evidence, build_plc_project, build_firmware_image, simulate_plc_runtime, validate_toolchain_matrix
from .ai_context import build_context


WEB_ROOT = Path(__file__).parents[2] / "web"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def create_server(database: str = "control-center.db", port: int = 8765) -> ThreadingHTTPServer:
    store = ProjectStore(database)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: object, content_type: str = "application/json") -> None:
            body = _json_bytes(payload) if content_type == "application/json" else payload
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            size = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(size) or b"{}")

        def _authorize(self, body: dict, action: str, project_id: str | None = None) -> None:
            actor_id = body.get("actorId") or self.headers.get("X-Actor-Id")
            tenant_id = body.get("tenantId") or self.headers.get("X-Tenant-Id")
            if not actor_id or not tenant_id:
                raise PermissionError("PM-AUTH-005: actorId and tenantId are required")
            actor = store.get_actor(actor_id, tenant_id, project_id)
            authorize(Actor(actor["actor_id"], actor["role"], actor["tenant_id"], frozenset(actor["project_ids"])), action, tenant_id=tenant_id, project_id=project_id)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Tenant-Id")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path == "/api/health":
                    return self._send(200, {"status": "ok", "service": "zhinen-pm", "contractVersion": "0.1"})
                if path == "/api/engineering/capabilities":
                    return self._send(200, {"capabilities": list_capabilities()})
                if path == "/api/projects":
                    return self._send(200, {"projects": store.list_projects()})
                if path == "/api/users":
                    tenant_id = urlparse(self.path).query.replace("tenantId=", "")
                    return self._send(200, {"users": store.list_users(tenant_id)})
                if path == "/api/notifications":
                    query = parse_qs(urlparse(self.path).query)
                    return self._send(200, {"notifications": store.list_notifications(query.get("recipientId", [""])[0], query.get("projectId", [None])[0])})
                if path.startswith("/api/projects/"):
                    project_id = path.split("/")[3]
                    if path.endswith("/tree"):
                        return self._send(200, {"tree": store.get_tree(project_id)})
                    if path.endswith("/members"):
                        return self._send(200, {"members": store.list_members(project_id)})
                    if path.endswith("/backlog"):
                        status = parse_qs(urlparse(self.path).query).get("status", [None])[0]
                        return self._send(200, {"items": store.list_backlog(project_id, status)})
                    if path.endswith("/sync-queue"):
                        return self._send(200, {"items": store.list_sync_queue(project_id)})
                    if path.endswith("/links"):
                        entity_id = parse_qs(urlparse(self.path).query).get("entityId", [None])[0]
                        return self._send(200, {"links": store.list_links(project_id, entity_id)})
                    if path.endswith("/search"):
                        query = parse_qs(urlparse(self.path).query).get("q", [""])[0]
                        return self._send(200, {"results": store.search(project_id, query)})
                    if path.endswith("/stats"):
                        return self._send(200, store.project_stats(project_id))
                    if path.endswith("/acceptance-report"):
                        return self._send(200, store.acceptance_report(project_id))
                    if path.endswith("/audit"):
                        return self._send(200, {"audit": store.list_audit(project_id)})
                    if path.endswith("/machine-objects"):
                        object_type = parse_qs(urlparse(self.path).query).get("type", [None])[0]
                        return self._send(200, {"objects": store.list_machine_objects(project_id, object_type)})
                    if path.endswith("/artifacts"):
                        return self._send(200, {"artifacts": store.list_artifact_manifests(project_id)})
                    if path.endswith("/machine-snapshots"):
                        return self._send(200, {"snapshots": store.list_snapshots(project_id)})
                    if path.endswith("/readiness"):
                        return self._send(200, {"items": store.backlog_readiness(project_id)})
                    if path.endswith("/capability-readiness"):
                        return self._send(200, {"capabilities": store.capability_evidence(project_id, [x["id"] for x in list_capabilities()])})
                    if path.endswith("/release-gate"):
                        release_id = parse_qs(urlparse(self.path).query).get("releaseId", [None])[0]
                        if not release_id:
                            return self._send(400, {"code": "PM-REQUEST-001", "message": "releaseId is required"})
                        return self._send(200, store.release_gate(release_id))
                    if path.endswith("/backlog"):
                        status = parse_qs(urlparse(self.path).query).get("status", [None])[0]
                        return self._send(200, {"items": store.list_backlog(project_id, status)})
                    if path.endswith("/entities"):
                        entity_type = parse_qs(urlparse(self.path).query).get("type", [None])[0]
                        return self._send(200, {"entities": store.list_entities(project_id, entity_type)})
                    return self._send(200, store.get_project(project_id))
                if path.startswith("/api/entities/"):
                    entity_id = path.split("/")[3]
                    return self._send(200, store.get_entity(entity_id))
                if path == "/" or path == "/index.html":
                    return self._send(200, (WEB_ROOT / "index.html").read_bytes(), "text/html")
                return self._send(404, {"code": "PM-NOT-FOUND", "message": "route not found"})
            except KeyError as exc:
                return self._send(404, {"code": "PM-NOT-FOUND", "message": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                body = self._body()
                if path == "/api/projects":
                    result = store.create_project(project_id=body["projectId"], tenant_id=body["tenantId"], name=body["name"], kind=body.get("kind", "platform"), owner_id=body["ownerId"])
                    return self._send(201, result)
                if path == "/api/users":
                    result = store.create_user(user_id=body["userId"], tenant_id=body["tenantId"], display_name=body.get("displayName", body["userId"]), role=body.get("role", "viewer"))
                    return self._send(201, result)
                if path.startswith("/api/projects/") and path.endswith("/members"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    return self._send(201, store.add_member(project_id=project_id, user_id=body["userId"], role=body["role"]))
                if path.startswith("/api/projects/") and path.endswith("/backlog/import"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    count = store.import_backlog(project_id=project_id, items=body["items"], actor_id=body["actorId"])
                    return self._send(201, {"inserted": count, "items": len(store.list_backlog(project_id))})
                if path.startswith("/api/projects/") and path.endswith("/sync-queue"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    result = store.enqueue_sync(sync_id=body["id"], project_id=project_id, tenant_id=body["tenantId"], direction=body["direction"], object_type=body["objectType"], object_id=body["objectId"], idempotency_key=body["idempotencyKey"], payload=body.get("payload", {}))
                    return self._send(201, result)
                if path.startswith("/api/projects/") and path.endswith("/links"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    return self._send(201, store.link_entities(project_id=project_id, from_id=body["fromId"], to_id=body["toId"], link_type=body["linkType"]))
                if path.startswith("/api/sync/") and path.endswith("/transition"):
                    sync = store.get_sync(path.split("/")[3])
                    self._authorize(body, "MODIFY", sync["project_id"])
                    result = store.transition_sync(path.split("/")[3], body["target"], body.get("reason", ""))
                    return self._send(200, result)
                if path.startswith("/api/projects/") and path.endswith("/notify"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    return self._send(201, store.notify(notification_id=body["id"], project_id=project_id, recipient_id=body["recipientId"], kind=body["kind"], message=body["message"]))
                if path.startswith("/api/notifications/") and path.endswith("/read"):
                    notification = store.get_notification(path.split("/")[3])
                    self._authorize(body, "MODIFY", notification["project_id"])
                    return self._send(200, store.mark_notification_read(path.split("/")[3]))
                if path.startswith("/api/projects/") and path.endswith("/backup"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    destination = str(Path("backups") / f"{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.db")
                    Path("backups").mkdir(exist_ok=True)
                    return self._send(201, {"projectId": project_id, "backup": store.backup(destination)})
                if path.startswith("/api/projects/") and path.endswith("/machine-objects"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    result = store.create_machine_object(object_id=body["id"], project_id=project_id, tenant_id=body["tenantId"], object_type=body["objectType"], name=body["name"], owner_id=body["ownerId"], payload=body.get("payload"), parent_id=body.get("parentId"))
                    return self._send(201, result)
                if path.startswith("/api/projects/") and path.endswith("/artifacts"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    result = store.create_artifact_manifest(artifact_id=body["id"], project_id=project_id, artifact_type=body["artifactType"], source_uri=body["sourceUri"], content_hash=body["contentHash"], artifact_revision=body["revision"], toolchain_version=body.get("toolchainVersion", "TBD"), target_environment=body.get("targetEnvironment", "LOCAL"), sensitivity=body.get("sensitivity", "INTERNAL"), owner_id=body["ownerId"])
                    return self._send(201, result)
                if path == "/api/engineering/validate":
                    return self._send(200, validate_capability(body["capabilityId"], body.get("payload", {})))
                if path == "/api/engineering/runtime-simulate":
                    return self._send(200, simulate_plc_runtime(int(body.get("cycles", 100)), int(body.get("cycleMs", 10)), int(body.get("watchdogMs", 50)), body.get("fault")))
                if path == "/api/engineering/toolchain-matrix":
                    return self._send(200, validate_toolchain_matrix(body.get("cases", [])))
                if path.startswith("/api/projects/") and path.endswith("/toolchain-matrix"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    validation = validate_toolchain_matrix(body.get("cases", []))
                    item = store.create_entity(entity_id=body["validationId"], entity_type="tool_validation", project_id=project_id, tenant_id=body["tenantId"], title="PLC/HMI toolchain matrix", owner_id=body["actorId"], payload=validation)
                    store.transition(entity_id=item["id"], target="RUNNING", actor_id=body["actorId"], expected_revision=1)
                    final = store.transition(entity_id=item["id"], target="VALIDATED" if validation["result"] == "PASSED" else "FAILED", actor_id=body["actorId"], expected_revision=2)
                    return self._send(201, {"validation": final, "matrix": validation})
                if path.startswith("/api/projects/") and path.endswith("/simulate"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    result = simulation_evidence(body["capabilityId"], body.get("payload", {}))
                    run = store.create_entity(entity_id=body["testRunId"], entity_type="test_run", project_id=project_id, tenant_id=body["tenantId"], title=f"{body['capabilityId']} simulation", owner_id=body["actorId"], payload=result)
                    evidence = store.create_entity(entity_id=body["evidenceId"], entity_type="evidence", project_id=project_id, tenant_id=body["tenantId"], title=f"{body['capabilityId']} simulation evidence", owner_id=body["actorId"], payload=result)
                    store.transition(entity_id=run["id"], target="RUNNING", actor_id=body["actorId"], expected_revision=1)
                    if result["result"] in {"PASSED", "CONTRACT_PASSED"}:
                        store.transition(entity_id=run["id"], target="PASSED", actor_id=body["actorId"], expected_revision=2)
                        store.transition(entity_id=evidence["id"], target="VALIDATED", actor_id=body["actorId"], expected_revision=1)
                        store.link_entities(project_id=project_id, from_id=body["releaseId"], to_id=evidence["id"], link_type="requires") if body.get("releaseId") else None
                    else:
                        store.transition(entity_id=run["id"], target="FAILED", actor_id=body["actorId"], expected_revision=2)
                    issue = None
                    if result["result"] not in {"PASSED", "CONTRACT_PASSED"}:
                        issue = store.create_entity(entity_id=body.get("issueId", f"ISSUE-{body['testRunId']}"), entity_type="issue", project_id=project_id, tenant_id=body["tenantId"], title=f"{body['capabilityId']} validation failed", owner_id=body["actorId"], payload={"sourceTestRunId": body["testRunId"], "evidenceId": body["evidenceId"], "capabilityId": body["capabilityId"], "errors": result.get("missing", [])})
                    return self._send(201, {"testRun": store.get_entity(run["id"]), "evidence": store.get_entity(evidence["id"]), "issue": issue, "validation": result})
                if path.startswith("/api/projects/") and path.endswith("/builds/plc"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    build = build_plc_project(body.get("source", ""), body.get("toolchainVersion", "SIMULATED-PLC-0.1"))
                    artifact = store.create_artifact_manifest(artifact_id=body["artifactId"], project_id=project_id, artifact_type="PLC", source_uri=body.get("sourceUri", "inline://plc"), content_hash=build["buildHash"], artifact_revision=body.get("artifactRevision", "r1"), toolchain_version=build["toolchainVersion"], target_environment="SIMULATION", sensitivity=body.get("sensitivity", "INTERNAL"), owner_id=body["actorId"])
                    run_id = body.get("testRunId", f"{body['artifactId']}-BUILD-RUN")
                    evidence_id = body.get("evidenceId", f"{body['artifactId']}-BUILD-EVIDENCE")
                    build_evidence = {**build, "capabilityId": "PLC-001", "evidenceType": "BUILD_RESULT"}
                    run = store.create_entity(entity_id=run_id, entity_type="test_run", project_id=project_id, tenant_id=body["tenantId"], title="PLC simulated build", owner_id=body["actorId"], payload=build_evidence)
                    evidence = store.create_entity(entity_id=evidence_id, entity_type="evidence", project_id=project_id, tenant_id=body["tenantId"], title="PLC build evidence", owner_id=body["actorId"], payload=build_evidence)
                    store.transition(entity_id=run_id, target="RUNNING", actor_id=body["actorId"], expected_revision=1)
                    if build["result"] == "PASSED":
                        store.transition(entity_id=run_id, target="PASSED", actor_id=body["actorId"], expected_revision=2)
                        store.transition(entity_id=evidence_id, target="VALIDATED", actor_id=body["actorId"], expected_revision=1)
                        store.transition_artifact(artifact_id=artifact["id"], target="BUILT", actor_id=body["actorId"])
                        store.transition_artifact(artifact_id=artifact["id"], target="TESTED", actor_id=body["actorId"])
                        if body.get("releaseId"):
                            store.link_entities(project_id=project_id, from_id=body["releaseId"], to_id=evidence_id, link_type="requires")
                    else:
                        store.transition(entity_id=run_id, target="FAILED", actor_id=body["actorId"], expected_revision=2)
                    issue = None
                    if build["result"] != "PASSED":
                        issue = store.create_entity(entity_id=body.get("issueId", f"ISSUE-{run_id}"), entity_type="issue", project_id=project_id, tenant_id=body["tenantId"], title="Firmware build failed", owner_id=body["actorId"], payload={"sourceTestRunId": run_id, "evidenceId": evidence_id, "capabilityId": "FW-001", "errors": build["errors"]})
                    return self._send(201, {"build": build, "artifact": store.get_artifact_manifest(body["artifactId"]), "testRun": store.get_entity(run_id), "evidence": store.get_entity(evidence_id), "issue": issue})
                if path.startswith("/api/projects/") and path.endswith("/builds/firmware"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    build = build_firmware_image(body.get("source", ""), body.get("toolchainVersion", "SIMULATED-FW-0.1"), body.get("target", "EDGE"), body.get("previousHash"), bool(body.get("injectPowerLoss", False)))
                    artifact = store.create_artifact_manifest(artifact_id=body["artifactId"], project_id=project_id, artifact_type="FIRMWARE", source_uri=body.get("sourceUri", "inline://firmware"), content_hash=build["imageHash"], artifact_revision=body.get("artifactRevision", "r1"), toolchain_version=build["toolchainVersion"], target_environment=build["target"], sensitivity=body.get("sensitivity", "EDGE_ONLY"), owner_id=body["actorId"])
                    run_id = body.get("testRunId", f"{body['artifactId']}-BUILD-RUN")
                    evidence_id = body.get("evidenceId", f"{body['artifactId']}-BUILD-EVIDENCE")
                    build_evidence = {**build, "capabilityId": "FW-001", "evidenceType": "BUILD_RESULT"}
                    run = store.create_entity(entity_id=run_id, entity_type="test_run", project_id=project_id, tenant_id=body["tenantId"], title="Firmware simulated build", owner_id=body["actorId"], payload=build_evidence)
                    evidence = store.create_entity(entity_id=evidence_id, entity_type="evidence", project_id=project_id, tenant_id=body["tenantId"], title="Firmware build evidence", owner_id=body["actorId"], payload=build_evidence)
                    store.transition(entity_id=run_id, target="RUNNING", actor_id=body["actorId"], expected_revision=1)
                    if build["result"] == "PASSED":
                        store.transition(entity_id=run_id, target="PASSED", actor_id=body["actorId"], expected_revision=2)
                        store.transition(entity_id=evidence_id, target="VALIDATED", actor_id=body["actorId"], expected_revision=1)
                        store.transition_artifact(artifact_id=artifact["id"], target="BUILT", actor_id=body["actorId"])
                        store.transition_artifact(artifact_id=artifact["id"], target="TESTED", actor_id=body["actorId"])
                    else:
                        store.transition(entity_id=run_id, target="FAILED", actor_id=body["actorId"], expected_revision=2)
                    return self._send(201, {"build": build, "artifact": store.get_artifact_manifest(body["artifactId"]), "testRun": store.get_entity(run_id), "evidence": store.get_entity(evidence_id)})
                if path.startswith("/api/projects/") and path.endswith("/test-runs/execute"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    result = store.execute_test_case(project_id=project_id, tenant_id=body["tenantId"], test_case_id=body["testCaseId"], run_id=body["runId"], evidence_id=body["evidenceId"], actor_id=body["actorId"], passed=bool(body.get("passed", False)), release_id=body.get("releaseId"))
                    return self._send(201, result)
                if path == "/api/ai/context":
                    return self._send(200, build_context(store, project_id=body["projectId"], object_ids=body.get("objectIds", []), actor_id=body["actorId"]))
                if path.startswith("/api/projects/") and path.endswith("/machine-snapshots"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    return self._send(201, store.snapshot_machine(snapshot_id=body["id"], project_id=project_id, machine_id=body["machineId"], created_by=body["actorId"]))
                if path.startswith("/api/machine-objects/") and path.endswith("/update"):
                    object_id = path.split("/")[3]
                    obj = store.get_machine_object(object_id)
                    self._authorize(body, "MODIFY", obj["project_id"])
                    return self._send(200, store.update_machine_object(object_id=object_id, name=body.get("name"), payload=body.get("payload"), expected_revision=body["expectedRevision"]))
                if path.startswith("/api/machine-snapshots/") and path.endswith("/diff"):
                    left_id = path.split("/")[3]
                    return self._send(200, store.diff_snapshots(left_id, body["rightId"]))
                if path.startswith("/api/projects/") and path.endswith("/backlog/import"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    count = store.import_backlog(project_id=project_id, items=body["items"], actor_id=body["actorId"])
                    return self._send(201, {"inserted": count, "items": len(store.list_backlog(project_id))})
                if path.startswith("/api/projects/") and path.endswith("/entities"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    result = store.create_entity(entity_id=body["id"], entity_type=body["type"], project_id=project_id, tenant_id=body["tenantId"], title=body["title"], owner_id=body["ownerId"], payload=body.get("payload"))
                    return self._send(201, result)
                if path.startswith("/api/projects/") and path.endswith("/tree"):
                    project_id = path.split("/")[3]
                    self._authorize(body, "MODIFY", project_id)
                    return self._send(201, store.add_node(project_id=project_id, node_id=body["id"], name=body["name"], node_type=body.get("nodeType", "section"), parent_id=body.get("parentId"), sort_order=int(body.get("sortOrder", 0))))
                if path.startswith("/api/entities/") and path.endswith("/transition"):
                    entity_id = path.split("/")[3]
                    entity = store.get_entity(entity_id)
                    self._authorize(body, "MODIFY", entity["project_id"])
                    result = store.transition(entity_id=entity_id, target=body["target"], actor_id=body.get("actorId") or self.headers.get("X-Actor-Id"), expected_revision=body["expectedRevision"])
                    return self._send(200, result)
                if path.startswith("/api/entities/") and path.endswith("/payload"):
                    entity_id = path.split("/")[3]
                    entity = store.get_entity(entity_id)
                    self._authorize(body, "MODIFY", entity["project_id"])
                    return self._send(200, store.update_entity_payload(entity_id=entity_id, payload=body.get("payload", {}), actor_id=body["actorId"], expected_revision=body["expectedRevision"]))
                if path.startswith("/api/entities/") and path.endswith("/apply"):
                    entity_id = path.split("/")[3]
                    entity = store.get_entity(entity_id)
                    self._authorize(body, "APPLY", entity["project_id"])
                    if not body.get("approvalId"):
                        raise PermissionError("PM-PARAM-001: approvalId is required")
                    return self._send(201, store.apply_parameter_snapshot(snapshot_id=entity_id, sync_id=body["syncId"], approval_id=body["approvalId"], actor_id=body["actorId"]))
                if path.startswith("/api/artifacts/") and path.endswith("/transition"):
                    artifact_id = path.split("/")[3]
                    artifact = store.get_artifact_manifest(artifact_id)
                    action = "APPROVE" if body["target"] == "APPROVED" else "MODIFY"
                    self._authorize(body, action, artifact["project_id"])
                    return self._send(200, store.transition_artifact(artifact_id=artifact_id, target=body["target"], actor_id=body["actorId"]))
                return self._send(404, {"code": "PM-NOT-FOUND", "message": "route not found"})
            except KeyError as exc:
                return self._send(400, {"code": "PM-REQUEST-001", "message": f"missing field: {exc.args[0]}"})
            except (ValueError, RuntimeError) as exc:
                return self._send(409, {"code": "PM-CONTRACT-001", "message": str(exc)})
            except PermissionError as exc:
                return self._send(403, {"code": "PM-AUTH-001", "message": str(exc)})
            except json.JSONDecodeError:
                return self._send(400, {"code": "PM-REQUEST-002", "message": "invalid JSON"})

        def log_message(self, *_args) -> None:
            return

    class PMServer(ThreadingHTTPServer):
        def server_close(self) -> None:
            store.close()
            super().server_close()

    return PMServer(("127.0.0.1", port), Handler)
