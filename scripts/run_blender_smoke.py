#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys


def main() -> int:
    blender = os.environ.get("BLENDER")
    if not blender:
        print("SKIP: set BLENDER=/path/to/blender to run the Blender smoke test")
        print("TIP: set BLENDEX_GENERATED_GRAPH_SMOKE=1 as well to include generated graph smoke coverage")
        return 0

    root = pathlib.Path(__file__).resolve().parents[1]
    script = root / "tests" / "integration" / "blender_smoke.py"
    if os.environ.get("BLENDEX_GENERATED_GRAPH_SMOKE"):
        print("Running Blender smoke with generated graph coverage")
    return subprocess.run([blender, "--background", "--factory-startup", "--python", str(script)]).returncode


if __name__ == "__main__":
    sys.exit(main())
