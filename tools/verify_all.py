"""Run the repository's complete software quality gate with one command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> None:
    print(f"== {label} ==")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run("Python contract and integration tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"])
    run("Machine Project schema", [sys.executable, "tools/validate_machine_project.py", "examples/machine-project.valid.json"])
    run("Management Center JavaScript syntax", ["node", "tools/check_web_syntax.js"])
    run("Patch whitespace", ["git", "diff", "--check"])
    print("verify-all-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
