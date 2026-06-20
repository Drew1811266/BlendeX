# BlendeX v0.5 Readiness Audit

Date: 2026-06-19

Version: 0.50.0

Status: Ready for semantic Geometry Nodes reasoning

## Scope

BlendeX v0.5 upgrades the v0.4 local beta from fixed recipe execution to a semantic Geometry Nodes reasoning system. The plugin can parse procedural modeling intent, choose relevant Geometry Nodes by effect semantics, synthesize typed graph IR, validate links and sockets, run bounded repairs, export structured operation batches, and preserve the v0.4 safety workflow for dry-run, confirmation, execution, inspection, history, and undo.

This audit does not declare arbitrary Blender automation, marketplace release readiness, photoreal character generation, simulation-zone authoring, or free-form Python execution.

## Completed Release Criteria

- Version metadata is synchronized at `0.50.0` across runtime, plugin manifest, Python project metadata, and Blender add-on metadata.
- The add-on package script builds `blendex-0.50.0-blender-addon.zip` with both `blendex` and `blendex_protocol`.
- MCP probe OK for the BlendeX server tool surface.
- The v0.5 held-out benchmark reports held-out benchmark: 20/20 valid graph plans.
- The same benchmark reports property pass: 20/20 for expected effects and minimum graph complexity.
- Anti-Template Requirement: satisfied. The benchmark is solved through `plan_graph`, node semantics, typed graph IR, validation, and repair rather than expected recipe ids.
- Real Blender smoke passed with Blender 5.1.2 using `/Applications/Blender.app/Contents/MacOS/Blender`.
- Generated graph smoke passed with `BLENDEX_GENERATED_GRAPH_SMOKE=1` and Blender 5.1.2, covering semantic graph execution beyond fixed recipes.

## Capability Review

- intent parsing: recognizes architecture, scatter, instance, deform, field, attribute, material, selection, simulation, and character boundaries.
- node semantics: records planner-ready effects, fields, attributes, instances, pairings, and repair hints for core Geometry Nodes.
- typed graph IR: represents nodes, links, socket values, dynamic group inputs, and operation-batch export.
- static validation: checks missing outputs, link endpoints, sockets, socket types, field/value mismatches, and instance realization rules.
- repair loop: adds missing group outputs, normalizes socket names, and inserts Realize Instances where required.
- advanced fields: builds Position/Normal -> Separate XYZ -> Compare selection masks.
- attributes: captures original fields, stores named attributes for material and later shading workflows.
- instances: composes Instance on Points with Realize Instances before mesh-only edits.
- group inputs: models exposed group controls and connects them into generated graph IR.

## Verification Commands

```bash
./scripts/run_release_checks.sh
python3 scripts/run_blender_smoke.py
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender python3 scripts/run_blender_smoke.py
BLENDEX_GENERATED_GRAPH_SMOKE=1 BLENDER=/Applications/Blender.app/Contents/MacOS/Blender python3 scripts/run_blender_smoke.py
python3 scripts/package_blender_addon.py --output-dir /tmp/blendex-v0-5-package-check
```

## Residual Limits

- v0.5 supports semantic procedural graph synthesis for the documented Geometry Nodes domains, not every Blender node or arbitrary art direction.
- Simulation and repeat-zone workflows are recognized but remain out of scope unless a future version defines safe bounded zone execution.
- Generated graph smoke requires a local Blender installation; when `BLENDER` is unset the launcher skips clearly and returns success.
- Dynamic group inputs are represented in BlendeX graph IR and validation; full Blender UI group-interface mutation remains a follow-up integration surface.
- Existing v0.4 recipes remain as compatibility paths for simple known prompts, but v0.5 readiness is judged by the anti-template held-out benchmark.

## Decision

BlendeX v0.5 meets the planned semantic Geometry Nodes reasoning readiness bar. The core target is achieved: CodeX now has a tested plugin path for understanding procedural modeling requests, choosing and composing Geometry Nodes, validating and repairing graph structure, and producing structured Blender operations without relying on fixed full-graph templates as the success mechanism.
