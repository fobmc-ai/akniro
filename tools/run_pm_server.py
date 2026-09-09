#!/usr/bin/env python3
"""Run the PM-0 development service placeholder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_pm.store import ProjectStore


if __name__ == "__main__":
    store = ProjectStore("control-center.db")
    print("PM-0 store initialized at control-center.db")
    store.close()
