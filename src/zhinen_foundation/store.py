"""Immutable JSON revision store for the V0.1 vertical slice."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .project import load_project, validate_project


class RevisionConflictError(RuntimeError):
    """Raised when a revision would overwrite an existing immutable revision."""


class ProjectStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.revisions = self.root / "revisions"
        self.revisions.mkdir(parents=True, exist_ok=True)

    def save(self, project: dict[str, Any]) -> Path:
        validate_project(project)
        target = self.revisions / f"{project['revision']}.json"
        if target.exists():
            existing = load_project(target)
            if existing != project:
                raise RevisionConflictError(f"immutable revision already exists: {project['revision']}")
            return target
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, target)
        return target

    def load(self, revision: str) -> dict[str, Any]:
        return load_project(self.revisions / f"{revision}.json")

    def list_revisions(self) -> tuple[str, ...]:
        return tuple(sorted(path.stem for path in self.revisions.glob("v*.json")))
