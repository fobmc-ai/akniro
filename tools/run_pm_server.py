#!/usr/bin/env python3
"""Run the PM-0 development HTTP service."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from zhinen_pm.server import create_server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="control-center.db")
    args = parser.parse_args()
    server = create_server(args.database)
    print(f"Zhinen PM running at http://127.0.0.1:8765 (database: {args.database})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
