#!/usr/bin/env python3
"""Validate a V0.1 JSON Machine Project without external dependencies."""

import argparse
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_foundation.project import ProjectValidationError, load_project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        load_project(args.project)
    except (OSError, ProjectValidationError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(f"VALID: {args.project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
