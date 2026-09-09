from __future__ import annotations

import hashlib
import json
from typing import Any


def build_suggestion(context: dict[str, Any], request: str) -> dict[str, Any]:
    """Build a deterministic, non-executable AI suggestion from governed context."""
    if not isinstance(request, str) or not request.strip():
        return {"result": "BLOCKED", "reason": "suggestion_request_required", "allowedActions": ["READ", "COMMENT", "SUGGEST"], "deniedActions": ["APPROVE", "RELEASE", "DEPLOY", "FORCE"]}
    object_ids = [item["id"] for item in context.get("objects", [])]
    omitted_ids = [item["id"] for item in context.get("omitted", [])]
    stable = {"projectId": context.get("projectId"), "request": request.strip(), "objectIds": object_ids, "omittedIds": omitted_ids}
    suggestion_hash = "sha256:" + hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"result": "SUGGESTED", "mode": "RULE_BASED_DRAFT", "request": request.strip(), "contextObjectIds": object_ids, "omittedObjectIds": omitted_ids, "recommendation": "将建议拆分为可评审的变更，并先执行对应 Test Plan；不得直接应用到现场。", "allowedActions": ["READ", "COMMENT", "SUGGEST"], "deniedActions": ["APPROVE", "RELEASE", "DEPLOY", "FORCE"], "suggestionHash": suggestion_hash, "deterministic": True, "requiresHumanReview": True, "applied": False}
