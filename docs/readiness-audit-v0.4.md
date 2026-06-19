# BlendeX v0.4 Readiness Audit

Date: 2026-06-19

Status: Ready for local beta

## Scope

BlendeX v0.4 is ready as a local beta for early testers who can install the Blender add-on, start the local service, connect the CodeX-side MCP plugin, plan supported recipe workflows, dry-run and confirm batches, inspect generated Geometry Nodes graphs, and undo the latest batch when a safe undo path is recorded.

This audit does not declare marketplace readiness, public distribution readiness, or broad arbitrary Geometry Nodes authoring support.

## Completed Release Criteria

- Version metadata is synchronized at `0.40.0` across runtime, plugin manifest, Python project metadata, Blender add-on metadata, and README.
- The add-on package script builds `blendex-0.40.0-blender-addon.zip` with both `blendex` and `blendex_protocol`.
- MCP probe OK for the BlendeX server tool surface.
- Unit and integration-style test suite passes through `./scripts/run_release_checks.sh`.
- Real Blender smoke passed with Blender 5.1.2 using `/Applications/Blender.app/Contents/MacOS/Blender`.
- The real Blender smoke covers a basic confirmed batch, `architecture.grid_tower`, and `scatter.ground_points`, including inspect and undo checks.
- Demo prompts document all six built-in recipes and the dry-run, confirm, inspect, and undo flow.

## Supported Recipes

- `architecture.grid_tower`
- `architecture.wall_panel`
- `architecture.modular_building`
- `scatter.stones`
- `scatter.ground_points`
- `scatter.grass`

## Capability Review

- Planner: keyword matching, simple parameter extraction, capability gating, and scoped unsupported responses are implemented.
- Recipe output: all six built-in recipes emit complete graph batches with carrier mesh creation, BlendeX-owned modifier creation, node creation, socket values, and links.
- Safety: mutating batches require confirmation, validate JSON-safe operation payloads, and execute only allowlisted operations.
- Local connection: WebSocket service is local-only and requires the Blender sidebar session token.
- Undo: object, modifier, node, socket value, link, and label changes have safe undo coverage when the batch succeeds and the runtime exposes enough state.
- UI: Blender sidebar exposes service status, auth status, recent operations, recent batch summaries, and undo status.
- Packaging: local beta zip generation is documented and tested.

## Verification Commands

```bash
./scripts/run_release_checks.sh
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender python3 scripts/run_blender_smoke.py
python3 scripts/package_blender_addon.py --output-dir /tmp/blendex-package-check
```

## Residual Limits

- v0.4 supports the six documented recipe workflows, not open-ended arbitrary Geometry Nodes generation.
- Real Blender smoke currently exercises one architecture recipe and one scattering recipe; the remaining four recipes are covered by unit tests and demo documentation.
- Recipe graph quality is suitable for local beta validation, but future versions should add richer generated geometry and broader Blender-version compatibility checks.
- The add-on package is a local beta artifact and has not gone through marketplace signing, review, or installer UX work.

## Decision

BlendeX v0.4 meets the planned local beta readiness bar. The remaining limitations are documented scope boundaries for future versions, not blockers for the v0.4 local beta goal.
