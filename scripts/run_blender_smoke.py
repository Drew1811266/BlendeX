#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys


def main() -> int:
    blender = os.environ.get("BLENDER")
    if not blender:
        print("SKIP: set BLENDER=/path/to/blender to run the Blender smoke test")
        return 0

    root = pathlib.Path(__file__).resolve().parents[1]
    script = root / "tests" / "integration" / "blender_smoke.py"
    return subprocess.run([blender, "--background", "--factory-startup", "--python", str(script)]).returncode


if __name__ == "__main__":
    sys.exit(main())
