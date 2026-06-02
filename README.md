# BlendeX

BlendeX is a Blender add-on and CodeX plugin MVP using a split bridge: the Blender add-on exposes a local WebSocket service, and the CodeX MCP tools call a structured Geometry Nodes executor. The MVP does not execute arbitrary AI-generated Python.

## Source Tree Setup

For local development, point Blender at the `blender_addon` directory. The add-on bootstraps the sibling `src` directory when running from this source tree so the shared `blendex_protocol` package is available inside Blender.

## Development Checks

Run the Python unit tests:

```bash
./scripts/run_unit_tests.sh
```

Run the Blender smoke test with a local Blender binary:

```bash
BLENDER=/path/to/blender python3 scripts/run_blender_smoke.py
```

If `BLENDER` is not set, the smoke runner prints a skip message and exits with status 0.
