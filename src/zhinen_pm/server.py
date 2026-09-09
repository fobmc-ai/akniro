from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .store import ProjectStore


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
                if path == "/api/projects":
                    return self._send(200, {"projects": store.list_projects()})
                if path.startswith("/api/projects/"):
                    project_id = path.split("/")[3]
                    if path.endswith("/tree"):
                        return self._send(200, {"tree": store.get_tree(project_id)})
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
                if path.startswith("/api/projects/") and path.endswith("/entities"):
                    project_id = path.split("/")[3]
                    result = store.create_entity(entity_id=body["id"], entity_type=body["type"], project_id=project_id, tenant_id=body["tenantId"], title=body["title"], owner_id=body["ownerId"], payload=body.get("payload"))
                    return self._send(201, result)
                if path.startswith("/api/entities/") and path.endswith("/transition"):
                    entity_id = path.split("/")[3]
                    result = store.transition(entity_id=entity_id, target=body["target"], actor_id=body["actorId"], expected_revision=body["expectedRevision"])
                    return self._send(200, result)
                return self._send(404, {"code": "PM-NOT-FOUND", "message": "route not found"})
            except KeyError as exc:
                return self._send(400, {"code": "PM-REQUEST-001", "message": f"missing field: {exc.args[0]}"})
            except (ValueError, RuntimeError) as exc:
                return self._send(409, {"code": "PM-CONTRACT-001", "message": str(exc)})
            except json.JSONDecodeError:
                return self._send(400, {"code": "PM-REQUEST-002", "message": "invalid JSON"})

        def log_message(self, *_args) -> None:
            return

    class PMServer(ThreadingHTTPServer):
        def server_close(self) -> None:
            store.close()
            super().server_close()

    return PMServer(("127.0.0.1", port), Handler)
