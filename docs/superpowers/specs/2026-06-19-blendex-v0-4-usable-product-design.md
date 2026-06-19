# BlendeX v0.4 Usable Product Design Spec

Date: 2026-06-19

## Summary

BlendeX v0.4 should turn the v0.3 early-user creative workflow into a fully usable local beta product. The project already has a safe split bridge, a CodeX-side MCP server, a Blender add-on WebSocket service, token authentication, allowlisted Geometry Nodes operations, dry-run, confirmed batch execution, batch history, limited undo, fixed recipes, and a keyword-based planner.

The v0.4 goal is to make that foundation useful for real procedural creation rather than only creating inspectable node sketches. A user should be able to install the project from source or a packaged add-on, connect CodeX to Blender with a visible token, ask for supported procedural assets in natural language, review a meaningful preview, confirm execution, see a visible Geometry Nodes result in Blender, inspect or adjust it, and undo supported BlendeX-owned changes with honest recovery states.

v0.4 is a local beta, not a marketplace release. It should be complete enough for real testers to use without developer hand-holding, but it will not promise unrestricted Blender automation, official Blender marketplace packaging, photoreal rendering workflows, asset-store integration, or arbitrary AI-generated Python execution.

## Product Definition

BlendeX v0.4 is complete when it satisfies these product-level outcomes:

- A new tester can follow the README to install the Blender add-on, configure the CodeX plugin, start the local service, copy the session token, and verify connection.
- CodeX can plan at least six supported creative workflows and produce operation batches that build complete, connected, visible Geometry Nodes graphs rather than unconnected node placeholders.
- At least one architecture or hard-surface workflow and one nature or scattering workflow are verified through real Blender background smoke tests when a local Blender executable is configured.
- The planner can handle a small but useful set of non-exact natural-language prompts by choosing recipes, normalizing parameters, or returning a scoped unsupported explanation with safe alternatives.
- Every mutating workflow goes through dry-run and explicit confirmation before execution.
- Batch history records enough information for audit, retry, user-facing summaries, and undo attempts.
- Undo is reliable for supported reversible batches and honest for unsupported or partial batches.
- Documentation describes the exact supported scope, setup flow, example prompts, troubleshooting, and known limits.
- A final readiness review proves each release criterion with current files, tests, and command output.

## Non-Goals

v0.4 will not:

- Execute arbitrary AI-generated Python in Blender.
- Promise success for every possible procedural modeling request.
- Mutate user-owned complex Geometry Nodes graphs unless the user explicitly marks them as BlendeX-owned.
- Ship an official Blender marketplace submission.
- Build a full chat UI inside Blender.
- Build a polished visual node graph diff UI.
- Implement advanced asset libraries, material authoring pipelines, animation systems, physics simulation, or photorealistic rendering.
- Replace CodeX reasoning with a full standalone procedural modeling engine.

## Current v0.3 Baseline

The current repository is at v0.3 / `0.30.0` and includes:

- Shared protocol request, response, validation, and structured error code modules.
- Blender add-on state, panel, service lifecycle, WebSocket framing, token authentication, main-thread dispatch, scene inspection, capability scanning, Geometry Nodes executor, safety validation, dry-run, batch execution, history, and conservative undo.
- CodeX-side MCP server, WebSocket client, tool definitions, semantic catalog, recipe registry, keyword planner, and confirmation summary helpers.
- Six v0.3 recipe ids:
  - `architecture.grid_tower`
  - `architecture.wall_panel`
  - `architecture.modular_building`
  - `scatter.stones`
  - `scatter.ground_points`
  - `scatter.grass`
- Unit tests for protocol, MCP tools/server/client, Blender add-on fake runtime, executor behavior, batch/history/undo, recipes, planner, and workflow helpers.
- A Blender background smoke script that currently verifies low-level modifier/node/batch/undo behavior when `BLENDER` is configured.

Important v0.3 limits that v0.4 must close:

- Recipes create carrier objects, modifiers, and labeled nodes, but they do not yet build fully connected, visible Geometry Nodes graphs.
- Planner matching is primarily keyword-based and does not extract meaningful parameters from user prompts.
- Semantic catalog is small and does not provide enough graph-building guidance for richer planning.
- Undo only supports simple created object/modifier/node batches.
- Real Blender smoke coverage does not yet prove complete recipe workflows.
- Documentation still mixes completed v0.3 capabilities with older future-roadmap items.
- Installation and local connection docs are developer-oriented rather than early-tester-oriented.

## Architecture Direction

v0.4 keeps the Split Bridge architecture:

```text
CodeX App
  |
  | MCP tools, planner, recipes, confirmation summaries
  v
CodeX BlendeX plugin
  |
  | local authenticated WebSocket / structured protocol
  v
Blender BlendeX add-on
  |
  | main-thread guarded bpy / owned Geometry Nodes mutations
  v
Blender scene and Geometry Nodes node trees
```

The main architectural additions are:

- A graph recipe DSL that can declare nodes, client ids, socket values, links, labels, and graph output expectations in a consistent way.
- More complete recipe builders for architecture and scattering workflows.
- Planner parameter extraction and capability-aware recipe selection.
- Readiness and smoke verification focused on real visible graphs, not only API success.
- Packaging and setup helpers for a local beta workflow.

The executor remains the only module that mutates Blender data. The CodeX side plans and builds structured operation batches only. The shared protocol continues to reject unsupported operations and invalid JSON values before Blender mutation.

## Recipe Graph Requirements

Every v0.4 built-in recipe must produce a complete graph batch with:

- A carrier mesh or selected target policy.
- A BlendeX-owned Geometry Nodes modifier.
- A final connection into the node group output when Blender exposes the required sockets.
- Meaningful labels for every created node.
- Parameters that affect either graph structure, socket values, labels, or both.
- A dry-run preview that lists objects, modifiers, nodes, links, socket values, warnings, and undo availability.
- Recipe metadata with supported prompts, parameters, required node types, and expected output description.

The first v0.4 target recipes are:

- Modular grid tower: creates a visible modular massing graph with floor/module controls.
- Procedural wall panel: creates a visible panel grid or repeated panel strip graph.
- Simple modular building: creates a visible building massing graph with floor and bay controls.
- Random stone scatter: creates a point distribution and instance workflow with density and seed controls.
- Ground point distribution: creates a visible point cloud or point-driven carrier graph.
- Simple grass scatter: creates a point distribution and grass-instance workflow with density and scale controls.

If a Blender runtime lacks a required node type or socket metadata, the recipe should fail before mutation with a clear error and a narrower supported alternative where possible.

## Planner Requirements

The v0.4 planner should be more useful without pretending to be fully open-ended. It should:

- Prefer stable recipes when a request matches supported categories.
- Extract simple parameters from prompts, such as floors, levels, columns, segments, density, seed, and scale.
- Use capability scan data to reject recipes that cannot run on the active Blender runtime.
- Return a dry-runnable batch for supported requests.
- Return `PLANNER_UNSUPPORTED_REQUEST` for requests outside scope, with suggested supported prompts.
- Preserve safety: no arbitrary Python, no mutation without confirmation, and no user-owned graph mutation by default.

The planner may remain deterministic and local in v0.4. It does not need to call an external model.

## Workflow Requirements

The normal v0.4 user workflow is:

1. Install or load the Blender add-on.
2. Start the BlendeX service from the Blender sidebar.
3. Copy the session token.
4. Start CodeX with `BLENDEX_SESSION_TOKEN` or `BLENDEX_TOKEN`.
5. Ask for a supported procedural asset.
6. CodeX calls capability scan and scene inspection.
7. CodeX plans a recipe or safe fallback batch.
8. CodeX calls dry-run and shows a confirmation summary.
9. User confirms.
10. CodeX executes the confirmed batch.
11. CodeX inspects the resulting tree and summarizes created object, modifier, graph nodes, links, and visible output expectation.
12. User can inspect batch history or undo when a safe undo path exists.

Read-only scan and inspect tools remain frictionless. Mutating operation batches must keep the existing confirmation requirement.

## Undo and Recovery Requirements

v0.4 should improve undo coverage for recipe-generated batches while remaining honest:

- Object, modifier, node creation undo should remain reliable.
- Link creation undo should remove created links when the batch recorded enough endpoint information.
- Socket value changes should either record previous values and restore them or mark undo unavailable before claiming reversibility.
- Partial batches should not claim full undo unless every applied mutation has a reliable inverse.
- Batch records should expose `undo_status`, `undo_error`, and mutation-state clarity for failures.

## Blender UI Requirements

The Blender panel should remain lightweight but become tester-friendly:

- Show service status, client connection status, auth status, port, and a copyable or fully visible token path.
- Show recent operation status and recent batch summaries.
- Show last error and retry hint when available.
- Provide Start Service, Stop Service, and Undo Last Batch actions.
- Avoid becoming a full chat UI or recipe browser in v0.4.

## Packaging and Documentation Requirements

v0.4 should support a local beta installation path:

- A documented source-tree add-on setup.
- A packaged add-on zip script or documented command.
- CodeX plugin setup instructions using the existing `.codex-plugin/plugin.json` and `.mcp.json`.
- Token setup instructions for `BLENDEX_SESSION_TOKEN` and `BLENDEX_TOKEN`.
- Example prompts for every built-in recipe.
- Troubleshooting for auth, connection, unsupported planner requests, missing node types, dry-run warnings, partial batches, and undo unavailable.
- A cleaned README that no longer lists completed v0.3 items as future work.

## Testing and Verification Requirements

v0.4 should add tests at four levels:

- Protocol and MCP tests for any new operations, schemas, parameters, and errors.
- Recipe and planner unit tests for graph completeness, parameter extraction, capability gating, and unsupported prompts.
- Fake Blender runtime tests for complete graph creation, links, socket values, batch history, and undo.
- Blender background smoke tests for at least one architecture recipe and one scattering recipe when `BLENDER` is configured.

The final release verification command set should include:

```bash
./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
git diff --check
PYTHONPATH=src:. python3 -m codex_plugin.blendex_mcp.server
```

The MCP server command is used as a stdio sanity check through scripted initialize/tools-list probes, not as a hanging manual process.

## Version Roadmap

The 0.4 track is split into ten small versions:

- 0.31: v0.4 baseline, release criteria, readiness harness, and README cleanup.
- 0.32: graph recipe DSL and complete recipe operation builders.
- 0.33: complete architecture recipes.
- 0.34: complete scattering recipes.
- 0.35: planner parameter extraction and capability gating.
- 0.36: dry-run, confirmation, and post-execution summaries for full graphs.
- 0.37: expanded undo for links and socket values.
- 0.38: Blender UI and local beta packaging improvements.
- 0.39: real Blender smoke expansion and demo prompt flows.
- 0.40: final metadata alignment, release docs, and readiness audit.

Each minor version must leave the repository testable. Production code changes must follow test-first development.

## Release Criteria

BlendeX v0.4 is complete only when all of these are proven:

- Metadata is aligned across `.codex-plugin/plugin.json`, `pyproject.toml`, Blender `bl_info`, and MCP server version reporting.
- README accurately describes v0.4 setup, capabilities, examples, troubleshooting, and limits.
- All six built-in recipes generate complete graph batches with nodes, links, and socket values where applicable.
- Planner can match supported prompts, extract simple parameters, honor capability constraints, and reject unsupported prompts clearly.
- Dry-run previews full graph changes and confirmation summaries are meaningful.
- Confirmed execution records batch history and post-execution inspect data.
- Undo succeeds for supported reversible recipe batches and returns clear unavailable states otherwise.
- Unit tests pass.
- Blender smoke test passes when `BLENDER` is configured, or skips clearly when not configured.
- A final readiness review document maps each release criterion to evidence.
