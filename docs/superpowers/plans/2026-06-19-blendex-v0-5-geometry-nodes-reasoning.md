# BlendeX v0.5 Geometry Nodes Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build BlendeX v0.5 as a Geometry Nodes reasoning system that can synthesize, validate, repair, and explain procedural node graphs without relying on fixed full-graph templates.

**Architecture:** Keep the v0.4 local service, safety, operation batch, inspect, and undo infrastructure. Add a Codex-side semantic planning stack: runtime node introspection, node knowledge, effect intent parsing, typed graph IR, bounded backward planning, Blender validation/repair, and benchmark-driven readiness gates.

**Tech Stack:** Python standard library, Blender Python API, existing BlendeX MCP plugin/add-on modules, unittest test suite, existing release/smoke scripts.

---

## File Structure

- Create `docs/superpowers/specs/2026-06-19-blendex-v0-5-geometry-nodes-reasoning-design.md`
  - Owns the v0.5 definition, scope, non-goals, architecture, anti-template acceptance bar, and phase map.
- Create `docs/superpowers/plans/2026-06-19-blendex-v0-5-geometry-nodes-reasoning.md`
  - Owns this executable task plan.
- Create `docs/benchmarks/v0-5-heldout-prompts.json`
  - Holds held-out prompts, expected effect tags, and minimum graph properties.
- Create `tests/codex_plugin/test_v0_5_docs.py`
  - Verifies v0.5 docs define the anti-template and reasoning acceptance bar.
- Create `tests/codex_plugin/test_v0_5_benchmark_fixture.py`
  - Verifies the held-out prompt fixture is valid and does not contain recipe ids as expected answers.
- Modify `blender_addon/blendex/capabilities.py`
  - Extend runtime node/socket introspection.
- Create `codex_plugin/blendex_mcp/node_schema.py`
  - Normalized capability and socket schema helpers.
- Create `codex_plugin/blendex_mcp/node_semantics.py`
  - Structured node semantic records, validation, and lookup.
- Modify `codex_plugin/blendex_mcp/catalog.py`
  - Keep compatibility wrapper around the new semantic catalog.
- Create `codex_plugin/blendex_mcp/effect_model.py`
  - Prompt-to-effect intent extraction.
- Create `codex_plugin/blendex_mcp/graph_ir.py`
  - Typed graph model and operation batch export.
- Create `codex_plugin/blendex_mcp/graph_validation.py`
  - Static graph validation.
- Create `codex_plugin/blendex_mcp/graph_planner.py`
  - Backward semantic graph planner.
- Create `codex_plugin/blendex_mcp/graph_repair.py`
  - Repair loop data model and common repair transforms.
- Modify `codex_plugin/blendex_mcp/planner.py`
  - Route open-ended requests to semantic planning while keeping v0.4 recipes as compatibility fallback.
- Modify `tests/codex_plugin/test_planner.py`
  - Add anti-template planner assertions.
- Create focused tests for each new module under `tests/codex_plugin/`.
- Modify `tests/integration/blender_smoke.py`
  - Add optional generated-graph smoke mode for v0.48+.
- Create `docs/readiness-audit-v0.5.md`
  - Final v0.50 readiness audit.

## Version Slice Overview

- v0.41: Reasoning specification and benchmark fixture.
- v0.42: Runtime node introspection v2.
- v0.43: Node semantics knowledge base.
- v0.44: Procedural intent model.
- v0.45: Graph IR and type system.
- v0.46: Backward graph planner.
- v0.47: Runtime validation and repair loop.
- v0.48: Procedural modeling benchmark.
- v0.49: Advanced fields, attributes, instances, and group inputs.
- v0.50: Readiness audit and version sync.

## Task 1: v0.41 Design Docs and Anti-Template Fixture

**Files:**
- Create: `docs/superpowers/specs/2026-06-19-blendex-v0-5-geometry-nodes-reasoning-design.md`
- Create: `docs/superpowers/plans/2026-06-19-blendex-v0-5-geometry-nodes-reasoning.md`
- Create: `docs/benchmarks/v0-5-heldout-prompts.json`
- Create: `tests/codex_plugin/test_v0_5_docs.py`
- Create: `tests/codex_plugin/test_v0_5_benchmark_fixture.py`

- [ ] **Step 1: Write failing docs test**

Create `tests/codex_plugin/test_v0_5_docs.py`:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/superpowers/specs/2026-06-19-blendex-v0-5-geometry-nodes-reasoning-design.md"
PLAN = ROOT / "docs/superpowers/plans/2026-06-19-blendex-v0-5-geometry-nodes-reasoning.md"


class V05DocsTest(unittest.TestCase):
    def test_design_spec_defines_reasoning_and_anti_template_bar(self):
        text = SPEC.read_text(encoding="utf-8")
        required_phrases = [
            "Geometry Nodes reasoning system",
            "not \"more templates\"",
            "Anti-Template Requirement",
            "held-out prompts",
            "fields",
            "attributes",
            "instances",
            "repair",
            "v0.50: Readiness Audit",
        ]
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_plan_splits_v0_5_into_ten_version_slices(self):
        text = PLAN.read_text(encoding="utf-8")
        for patch in range(41, 51):
            with self.subTest(patch=patch):
                self.assertIn(f"v0.{patch}", text)
        self.assertIn("Backward graph planner", text)
        self.assertIn("Runtime validation and repair loop", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run docs test to verify it fails**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_v0_5_docs -v
```

Expected: FAIL because the spec and/or plan files do not exist yet.

- [ ] **Step 3: Add design spec and implementation plan**

Add the two v0.5 documents exactly as planned in this task. The design spec must
define current baseline, research notes, "understanding", supported scope,
architecture, anti-template requirement, version slices, and final acceptance.

- [ ] **Step 4: Write failing benchmark fixture test**

Create `tests/codex_plugin/test_v0_5_benchmark_fixture.py`:

```python
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/benchmarks/v0-5-heldout-prompts.json"


class V05BenchmarkFixtureTest(unittest.TestCase):
    def test_fixture_contains_heldout_prompts_without_recipe_answers(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], "0.5")
        prompts = data["prompts"]
        self.assertGreaterEqual(len(prompts), 20)
        recipe_prefixes = ("architecture.", "scatter.")
        for item in prompts:
            with self.subTest(prompt=item.get("id")):
                self.assertIsInstance(item["prompt"], str)
                self.assertGreaterEqual(len(item["expected_effects"]), 1)
                self.assertNotIn("recipe_id", item)
                self.assertFalse(item["id"].startswith(recipe_prefixes))
                self.assertIn("minimum_nodes", item)
                self.assertGreaterEqual(item["minimum_nodes"], 3)

    def test_fixture_covers_core_reasoning_domains(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        effects = {effect for item in data["prompts"] for effect in item["expected_effects"]}
        for effect in {
            "architecture",
            "scatter",
            "instance",
            "deform",
            "field",
            "attribute",
            "material",
            "selection",
        }:
            with self.subTest(effect=effect):
                self.assertIn(effect, effects)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run benchmark fixture test to verify it fails**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_v0_5_benchmark_fixture -v
```

Expected: FAIL because `docs/benchmarks/v0-5-heldout-prompts.json` does not exist yet.

- [ ] **Step 6: Add benchmark fixture**

Create `docs/benchmarks/v0-5-heldout-prompts.json` with at least 20 prompt records.
Every record must contain:

```json
{
  "id": "heldout_scatter_slope_pebbles",
  "prompt": "scatter uneven small pebbles across a sloped ground surface with random scale",
  "expected_effects": ["scatter", "instance", "field"],
  "minimum_nodes": 5,
  "notes": "Should require distribution, random variation, instancing, and final geometry output."
}
```

- [ ] **Step 7: Run v0.41 tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_v0_5_docs tests.codex_plugin.test_v0_5_benchmark_fixture -v
```

Expected: PASS.

- [ ] **Step 8: Commit v0.41 docs**

Run:

```bash
git add docs/superpowers/specs/2026-06-19-blendex-v0-5-geometry-nodes-reasoning-design.md docs/superpowers/plans/2026-06-19-blendex-v0-5-geometry-nodes-reasoning.md docs/benchmarks/v0-5-heldout-prompts.json tests/codex_plugin/test_v0_5_docs.py tests/codex_plugin/test_v0_5_benchmark_fixture.py
git commit -m "docs: define BlendeX v0.5 reasoning target"
```

Expected: commit succeeds.

## Task 2: v0.42 Runtime Node Introspection v2

**Files:**
- Modify: `blender_addon/blendex/capabilities.py`
- Create: `codex_plugin/blendex_mcp/node_schema.py`
- Create: `tests/blender_addon/test_capabilities_v2.py`
- Create: `tests/codex_plugin/test_node_schema.py`

- [ ] **Step 1: Write node schema tests**

Create tests that require normalized sockets with `name`, `identifier`,
`socket_type`, `is_multi_input`, `default_value`, `enum_items`, `is_field`, and
`metadata_complete`.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_node_schema tests.blender_addon.test_capabilities_v2 -v
```

Expected: FAIL because the schema module and richer capability fields are missing.

- [ ] **Step 3: Implement schema helpers**

Create `node_schema.py` with dataclass-free dictionary helpers so existing JSON
payloads remain simple and compatible.

- [ ] **Step 4: Extend capability scanning**

Update `capabilities.py` to read richer socket attributes defensively with
`getattr`, preserving current fake-runtime compatibility.

- [ ] **Step 5: Verify targeted tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_node_schema tests.blender_addon.test_capabilities_v2 tests.blender_addon.test_capabilities_fake -v
```

Expected: PASS.

- [ ] **Step 6: Commit v0.42**

Commit message:

```bash
git commit -m "feat: enrich Geometry Nodes capability metadata"
```

## Task 3: v0.43 Node Semantics Knowledge Base

**Files:**
- Create: `codex_plugin/blendex_mcp/node_semantics.py`
- Modify: `codex_plugin/blendex_mcp/catalog.py`
- Create: `tests/codex_plugin/test_node_semantics.py`
- Modify: `tests/blender_addon/test_capabilities_fake.py`

- [ ] **Step 1: Write semantic record validation tests**

Tests must require deep semantic records to expose `node_type`, `role`,
`effects`, `inputs`, `outputs`, `preconditions`, `postconditions`, `field_behavior`,
`instance_behavior`, `pairings`, and `repair_hints`.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_node_semantics -v
```

Expected: FAIL because `node_semantics.py` is missing.

- [ ] **Step 3: Implement semantic records**

Add validated records for the first core nodes: group input/output, join geometry,
transform geometry, set position, distribute points on faces, instance on points,
realize instances, random value, math, vector math, capture attribute, store named
attribute, set material, position, normal, index, object info, collection info, mesh
cube, mesh line, grid, extrude mesh, curve to mesh.

- [ ] **Step 4: Preserve catalog compatibility**

Keep `semantic_for_node(node_type)` returning a deep copy compatible with existing
capability scanning.

- [ ] **Step 5: Verify targeted tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_node_semantics tests.blender_addon.test_capabilities_fake -v
```

Expected: PASS.

- [ ] **Step 6: Commit v0.43**

Commit message:

```bash
git commit -m "feat: add structured node semantics"
```

## Task 4: v0.44 Procedural Intent Model

**Files:**
- Create: `codex_plugin/blendex_mcp/effect_model.py`
- Create: `tests/codex_plugin/test_effect_model.py`

- [ ] **Step 1: Write intent parser tests**

Tests must cover architecture, scattering, instancing, deformation, field-driven
variation, attribute capture/storage, material assignment, unsupported simulation,
and unsupported photoreal character requests.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_effect_model -v
```

Expected: FAIL because `effect_model.py` is missing.

- [ ] **Step 3: Implement `parse_effect_intent`**

Return a JSON-safe dictionary with `primary_effect`, `effects`, `parameters`,
`constraints`, `unsupported_reasons`, and `explanation`.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_effect_model -v
```

Expected: PASS.

- [ ] **Step 5: Commit v0.44**

Commit message:

```bash
git commit -m "feat: parse procedural modeling intents"
```

## Task 5: v0.45 Graph IR and Type System

**Files:**
- Create: `codex_plugin/blendex_mcp/graph_ir.py`
- Create: `codex_plugin/blendex_mcp/graph_validation.py`
- Create: `tests/codex_plugin/test_graph_ir.py`
- Create: `tests/codex_plugin/test_graph_validation.py`

- [ ] **Step 1: Write graph IR tests**

Tests must create graph IR for a source geometry, random field, distribute points,
instance on points, realize instances, join geometry, and group output.

- [ ] **Step 2: Verify graph IR tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_graph_ir tests.codex_plugin.test_graph_validation -v
```

Expected: FAIL because graph IR modules are missing.

- [ ] **Step 3: Implement IR helpers**

Implement JSON-safe graph dictionaries and builder functions. Avoid classes unless
they reduce real complexity.

- [ ] **Step 4: Implement static validation**

Validate unique node ids, known sockets, compatible link roles, one final geometry
output, and common field/value mismatch cases.

- [ ] **Step 5: Export operation batches**

Use existing `GraphRecipeBatch` operation shape so Blender safety and undo keep
working.

- [ ] **Step 6: Verify tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_graph_ir tests.codex_plugin.test_graph_validation tests.codex_plugin.test_graph_recipe -v
```

Expected: PASS.

- [ ] **Step 7: Commit v0.45**

Commit message:

```bash
git commit -m "feat: add typed Geometry Nodes graph IR"
```

## Task 6: v0.46 Backward Graph Planner

**Files:**
- Create: `codex_plugin/blendex_mcp/graph_planner.py`
- Modify: `codex_plugin/blendex_mcp/planner.py`
- Create: `tests/codex_plugin/test_graph_planner.py`
- Modify: `tests/codex_plugin/test_planner.py`

- [ ] **Step 1: Write anti-template planner tests**

Tests must disable or ignore recipe matching for held-out prompts and assert that
semantic graph planning returns `mode: "graph_plan"` with operations and explanation.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_graph_planner tests.codex_plugin.test_planner -v
```

Expected: FAIL because semantic graph planning is missing.

- [ ] **Step 3: Implement planner candidate selection**

Use effect intent and node semantics to select candidate nodes by postconditions.

- [ ] **Step 4: Implement bounded backward chaining**

Satisfy required geometry/field/value preconditions up to a fixed small depth.

- [ ] **Step 5: Implement scoring and explanations**

Score fewer invalid assumptions, fewer nodes, direct effect coverage, deterministic
random seeds, and Blender capability availability.

- [ ] **Step 6: Route open-ended planning**

Update `planner.py` so held-out requests can use semantic graph planning while old
recipe prompts remain compatible.

- [ ] **Step 7: Verify tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_graph_planner tests.codex_plugin.test_planner tests.codex_plugin.test_recipes -v
```

Expected: PASS.

- [ ] **Step 8: Commit v0.46**

Commit message:

```bash
git commit -m "feat: synthesize graphs from procedural intents"
```

## Task 7: v0.47 Runtime Validation and Repair Loop

**Files:**
- Create: `codex_plugin/blendex_mcp/graph_repair.py`
- Modify: `codex_plugin/blendex_mcp/server.py`
- Modify: `blender_addon/blendex/executor.py`
- Create: `tests/codex_plugin/test_graph_repair.py`
- Modify: `tests/codex_plugin/test_server.py`
- Modify: `tests/blender_addon/test_executor_fake.py`

- [ ] **Step 1: Write repair tests**

Tests must cover missing group output, missing source geometry, invalid socket name,
field/value mismatch, missing realize instances, and unsupported node type.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_graph_repair -v
```

Expected: FAIL because repair module is missing.

- [ ] **Step 3: Implement static repair transforms**

Return repaired graph plus trace entries. Keep retries bounded.

- [ ] **Step 4: Add runtime validation hook**

Use existing dry-run/inspect mechanisms to surface graph issues before confirmed
execution.

- [ ] **Step 5: Verify tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_graph_repair tests.codex_plugin.test_server tests.blender_addon.test_executor_fake -v
```

Expected: PASS.

- [ ] **Step 6: Commit v0.47**

Commit message:

```bash
git commit -m "feat: repair generated Geometry Nodes graphs"
```

## Task 8: v0.48 Procedural Modeling Benchmark

**Files:**
- Create: `codex_plugin/blendex_mcp/benchmark.py`
- Create: `tests/codex_plugin/test_benchmark.py`
- Modify: `tests/integration/blender_smoke.py`
- Modify: `scripts/run_blender_smoke.py`

- [ ] **Step 1: Write benchmark tests**

Tests must load held-out prompts, run semantic planning, validate graph properties,
and summarize pass/fail by effect category.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_benchmark -v
```

Expected: FAIL because benchmark runner is missing.

- [ ] **Step 3: Implement fake-runtime benchmark**

Run all held-out prompts against a fake capability map and require at least 20 valid
graph plans.

- [ ] **Step 4: Add optional real Blender benchmark mode**

When `BLENDER` is set, run a bounded subset through real Blender smoke.

- [ ] **Step 5: Verify tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_benchmark -v
```

Expected: PASS.

- [ ] **Step 6: Commit v0.48**

Commit message:

```bash
git commit -m "test: add procedural modeling benchmark"
```

## Task 9: v0.49 Advanced Field, Attribute, and Instance Composition

**Files:**
- Modify: `codex_plugin/blendex_mcp/node_semantics.py`
- Modify: `codex_plugin/blendex_mcp/graph_planner.py`
- Modify: `codex_plugin/blendex_mcp/graph_validation.py`
- Modify: `codex_plugin/blendex_mcp/graph_ir.py`
- Create: `tests/codex_plugin/test_advanced_geometry_nodes.py`

- [ ] **Step 1: Write advanced composition tests**

Tests must cover capture attribute before deformation, store named attribute for
material variation, selection mask generation, instance realization before mesh-only
operations, and exposed group inputs.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_advanced_geometry_nodes -v
```

Expected: FAIL because advanced composition rules are missing.

- [ ] **Step 3: Extend semantics and planner rules**

Add rules for attributes, fields, selections, random variation, instance realization,
and group inputs.

- [ ] **Step 4: Add constrained zone handling**

Recognize simulation/repeat-zone requests. Support only documented safe cases or
return a specific unsupported reason.

- [ ] **Step 5: Verify tests pass**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_advanced_geometry_nodes tests.codex_plugin.test_graph_planner tests.codex_plugin.test_graph_validation -v
```

Expected: PASS.

- [ ] **Step 6: Commit v0.49**

Commit message:

```bash
git commit -m "feat: compose field attribute and instance graphs"
```

## Task 10: v0.50 Readiness Audit and Release Sync

**Files:**
- Create: `docs/readiness-audit-v0.5.md`
- Modify: version metadata files discovered by `rg "0\\.40\\.0|0.40.0|0\\.4|v0.4"`
- Modify: `tests/codex_plugin/test_version.py`
- Modify: `tests/codex_plugin/test_readiness.py`
- Modify: `README.md`

- [ ] **Step 1: Write readiness tests**

Tests must require v0.50.0 version metadata, v0.5 readiness audit, anti-template
benchmark result language, and updated README scope.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_version tests.codex_plugin.test_readiness -v
```

Expected: FAIL because version metadata and readiness audit are not yet updated.

- [ ] **Step 3: Sync version metadata**

Update all release metadata to `0.50.0`.

- [ ] **Step 4: Write readiness audit**

Document supported domains, anti-template benchmark results, real Blender smoke
status, residual limits, and final v0.5 decision.

- [ ] **Step 5: Run release checks**

Run:

```bash
./scripts/run_release_checks.sh
```

Expected: PASS.

- [ ] **Step 6: Run real Blender smoke when Blender exists**

Run:

```bash
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender python3 scripts/run_blender_smoke.py
```

Expected: PASS when Blender is installed at that path. If unavailable, record the
environment limitation in the readiness audit.

- [ ] **Step 7: Package add-on**

Run:

```bash
python3 scripts/package_blender_addon.py --output-dir /tmp/blendex-v0-5-package-check
```

Expected: package file named `blendex-0.50.0-blender-addon.zip`.

- [ ] **Step 8: Commit v0.50**

Commit message:

```bash
git commit -m "chore: finalize BlendeX v0.5 readiness"
```

## Final Verification

After Task 10:

- Run `git status --short` and confirm only intentional files are changed or the
  tree is clean after commit.
- Run `./scripts/run_release_checks.sh`.
- Run real Blender smoke if Blender is available.
- Run package generation.
- Confirm `docs/readiness-audit-v0.5.md` states whether v0.5 meets the target.

## Self-Review

- Spec coverage: every requested v0.5 capability maps to at least one task.
- Anti-template requirement: covered by Task 1, Task 6, Task 8, and Task 10.
- Runtime validation and repair: covered by Task 7.
- Geometry Nodes understanding: covered by Tasks 2, 3, 4, 5, 6, and 9.
- Final readiness audit: covered by Task 10.
- Placeholder scan: no task uses `TBD`, `TODO`, or "implement later" as acceptance.
