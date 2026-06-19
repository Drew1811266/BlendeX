#!/usr/bin/env bash
set -euo pipefail

./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
PYTHONPATH=src:. python3 scripts/mcp_probe.py
git diff --check
