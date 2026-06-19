# BlendeX v0.4 Usable Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build BlendeX v0.4 as a fully usable local beta where CodeX can plan, preview, confirm, execute, inspect, and undo supported visible Geometry Nodes workflows in Blender.

**Architecture:** Keep the existing split bridge and deepen the CodeX-side planning layer plus Blender-side graph execution reliability. Add a graph recipe DSL, complete connected recipe batches, parameter extraction, capability gating, improved undo, packaging helpers, smoke coverage, and a final readiness audit. Preserve the core safety invariant: CodeX never sends arbitrary Python and Blender mutates only allowlisted BlendeX-owned graph surfaces.

**Tech Stack:** Python 3.9+, Blender `bpy`, stdlib `unittest`, stdlib WebSocket transport, stdio MCP server, existing BlendeX protocol package, shell scripts for local verification.

---

## Source Documents

- Spec: `docs/superpowers/specs/2026-06-19-blendex-v0-4-usable-product-design.md`
- Current v0.3 plan: `docs/superpowers/plans/2026-06-13-blendex-v0-3-creative-workflow.md`
- Current README: `README.md`

## Implementation Rules

- Use TDD for production code. Each behavior starts with a failing test, then minimal implementation, then refactor.
- Keep each minor version independently testable.
- Update version metadata at the start of each minor version.
- Do not execute arbitrary AI-generated Python in Blender.
- Keep mutations restricted to BlendeX-owned modifiers and node groups unless an operation is explicitly read-only or explicitly creates/marks ownership.
- Run `./scripts/run_unit_tests.sh` before each minor-version checkpoint.
- Run `python3 scripts/run_blender_smoke.py` after smoke-related changes. It may skip when `BLENDER` is unset, but must not mask failures when configured.
- Run `git diff --check` before every checkpoint.

## Planned File Structure

- `codex_plugin/blendex_mcp/version.py`
  - Version source of truth for the MCP server and plugin metadata.
- `codex_plugin/blendex_mcp/graph_recipe.py`
  - New graph recipe DSL for nodes, socket values, links, labels, expected outputs, and batch generation.
- `codex_plugin/blendex_mcp/recipes.py`
  - Existing recipe registry, migrated to graph recipe builders.
- `codex_plugin/blendex_mcp/planner.py`
  - Prompt matching, parameter extraction, capability gating, and unsupported-request guidance.
- `codex_plugin/blendex_mcp/workflow.py`
  - Dry-run confirmation summaries and post-execution summaries.
- `codex_plugin/blendex_mcp/tools.py`
  - MCP tool metadata and schemas if new recipe/planner result fields need exposure.
- `blender_addon/blendex/executor.py`
  - Geometry Nodes executor behavior, including group I/O initialization and link/socket mutation support.
- `blender_addon/blendex/batches.py`
  - Batch execution, inverse operation recording, and improved undo callbacks.
- `blender_addon/blendex/safety.py`
  - Batch validation and dry-run preview for complete graphs.
- `blender_addon/blendex/ui.py`
  - Tester-friendly panel refinements.
- `blender_addon/blendex/__init__.py`
  - Version metadata and operators.
- `scripts/package_blender_addon.py`
  - New local beta add-on zip packaging helper.
- `scripts/mcp_probe.py`
  - New MCP initialize/tools-list sanity probe.
- `scripts/run_release_checks.sh`
  - New release verification wrapper.
- `tests/codex_plugin/test_graph_recipe.py`
  - New DSL unit tests.
- `tests/codex_plugin/test_recipes.py`
  - Recipe completeness tests.
- `tests/codex_plugin/test_planner.py`
  - Planner parameter extraction and capability gating tests.
- `tests/codex_plugin/test_workflow.py`
  - Confirmation and post-execution summary tests.
- `tests/blender_addon/test_executor_fake.py`
  - Executor group I/O, link, and socket behavior tests.
- `tests/blender_addon/test_batches.py`
  - Undo coverage for links and socket values.
- `tests/blender_addon/test_safety.py`
  - Dry-run preview coverage for complete graph batches.
- `tests/integration/blender_smoke.py`
  - Real Blender recipe smoke tests.
- `README.md`
  - v0.4 local beta setup, examples, troubleshooting, and known limits.
- `docs/superpowers/reviews/2026-06-19-blendex-v0-4-readiness.md`
  - Final requirement-by-requirement readiness audit.

---

## Stage 0.31: Baseline, Release Criteria, and Readiness Harness

**Purpose:** Start the 0.4 track cleanly and create verification scaffolding before changing graph behavior.

**Files:**
- Modify: `codex_plugin/blendex_mcp/version.py`
- Modify: `.codex-plugin/plugin.json`
- Modify: `pyproject.toml`
- Modify: `blender_addon/blendex/__init__.py`
- Modify: `README.md`
- Create: `scripts/mcp_probe.py`
- Create: `scripts/run_release_checks.sh`
- Create: `tests/codex_plugin/test_version.py` additions

### Task 0.31.1: Version metadata starts 0.31.0

- [ ] **Step 1: Write the failing version test**

Add assertions to `tests/codex_plugin/test_version.py`:

```python
    def test_v0_4_track_starts_at_0_31(self):
        self.assertEqual(VERSION, "0.31.0")
```

- [ ] **Step 2: Run the targeted test**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_version -v
```

Expected: FAIL because current metadata is `0.30.0`.

- [ ] **Step 3: Update version metadata**

Set:

```python
# codex_plugin/blendex_mcp/version.py
VERSION = "0.31.0"
```

Set:

```toml
# pyproject.toml
version = "0.31.0"
```

Set:

```json
// .codex-plugin/plugin.json
"version": "0.31.0"
```

Set:

```python
# blender_addon/blendex/__init__.py
"version": (0, 31, 0),
```

- [ ] **Step 4: Run version tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_version -v
```

Expected: PASS.

### Task 0.31.2: MCP probe script

- [ ] **Step 1: Write failing tests for probe behavior**

Add a `VersionTests` assertion that `scripts/mcp_probe.py` exists and contains calls to `initialize` and `tools/list`:

```python
    def test_mcp_probe_script_exists(self):
        probe = ROOT / "scripts" / "mcp_probe.py"
        text = probe.read_text()

        self.assertIn('"method": "initialize"', text)
        self.assertIn('"method": "tools/list"', text)
```

- [ ] **Step 2: Run the targeted test**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_version.VersionTests.test_mcp_probe_script_exists -v
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Create `scripts/mcp_probe.py`**

The script should import `handle_line`, instantiate `BlenderClient`, send an initialize request and tools/list request, assert the server version matches `VERSION`, assert at least 18 tools are listed, and print a compact success line.

- [ ] **Step 4: Run the probe**

Run:

```bash
PYTHONPATH=src:. python3 scripts/mcp_probe.py
```

Expected:

```text
MCP probe OK: blendex 0.31.0, 18 tools
```

### Task 0.31.3: Release check wrapper

- [ ] **Step 1: Write failing test for release check script**

Add a `VersionTests` assertion that `scripts/run_release_checks.sh` exists and invokes unit tests, smoke test, diff check, and MCP probe:

```python
    def test_release_check_script_runs_required_commands(self):
        script = ROOT / "scripts" / "run_release_checks.sh"
        text = script.read_text()

        self.assertIn("./scripts/run_unit_tests.sh", text)
        self.assertIn("python3 scripts/run_blender_smoke.py", text)
        self.assertIn("git diff --check", text)
        self.assertIn("python3 scripts/mcp_probe.py", text)
```

- [ ] **Step 2: Run the targeted test**

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Create executable release check script**

Create a POSIX shell script with `set -euo pipefail` that runs:

```bash
./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
PYTHONPATH=src:. python3 scripts/mcp_probe.py
git diff --check
```

- [ ] **Step 4: Run release checks**

Run:

```bash
./scripts/run_release_checks.sh
```

Expected: unit tests pass, smoke passes or clearly skips, MCP probe passes, diff check passes.

### Task 0.31.4: README cleanup for v0.4 track

- [ ] **Step 1: Write failing README assertions**

Add tests in `tests/codex_plugin/test_version.py` verifying README mentions v0.4 local beta and no longer lists token auth, confirmation, and batch undo as future work.

- [ ] **Step 2: Run the targeted tests**

Expected: FAIL because README still contains old future-roadmap items.

- [ ] **Step 3: Update README**

Rewrite the status and roadmap sections to describe:

- v0.3 current baseline.
- v0.4 active goal.
- Supported v0.3 paths.
- v0.4 planned improvements.
- Release check commands.

- [ ] **Step 4: Run targeted and full tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_version -v
./scripts/run_release_checks.sh
```

Expected: PASS or smoke skip when `BLENDER` is unset.

---

## Stage 0.32: Graph Recipe DSL and Complete Batch Builders

**Purpose:** Introduce a reusable local DSL so recipes can declare complete graphs without hand-writing operation dictionaries in every builder.

**Files:**
- Create: `codex_plugin/blendex_mcp/graph_recipe.py`
- Create: `tests/codex_plugin/test_graph_recipe.py`
- Modify: `codex_plugin/blendex_mcp/recipes.py`
- Modify: `tests/codex_plugin/test_recipes.py`

### Task 0.32.1: Graph recipe model

- [ ] **Step 1: Write failing tests**

Create tests that construct a `GraphRecipeBatch` with object name, modifier name, nodes, socket values, and links. Assert that `to_operations()` emits:

- `scene.create_carrier_mesh`
- `geometry_nodes.create_modifier`
- `geometry_nodes.create_node`
- `geometry_nodes.set_socket_value`
- `geometry_nodes.link_sockets`

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_graph_recipe -v
```

Expected: FAIL because `graph_recipe.py` does not exist.

- [ ] **Step 3: Implement minimal DSL**

Add dataclasses:

- `GraphNodeSpec`
- `GraphSocketValueSpec`
- `GraphLinkSpec`
- `GraphRecipeBatch`

The DSL should generate deterministic operation ids and preserve client ids.

- [ ] **Step 4: Verify GREEN**

Run the targeted tests, then `./scripts/run_unit_tests.sh`.

### Task 0.32.2: Complete graph shape assertions

- [ ] **Step 1: Add recipe completeness tests**

For every built-in recipe, assert generated operations include at least one node, at least one link, at least one socket value or parameter-driven label, and a final output link expectation when the recipe declares output sockets.

- [ ] **Step 2: Verify RED**

Expected: FAIL because current recipes emit nodes only.

- [ ] **Step 3: Migrate recipes to graph DSL skeleton**

Update recipe builders to use `GraphRecipeBatch`. At this stage, it is acceptable for some recipes to emit simple graph links and socket values that fake-runtime tests can validate.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_graph_recipe tests.codex_plugin.test_recipes -v
./scripts/run_unit_tests.sh
```

---

## Stage 0.33: Complete Architecture Recipes

**Purpose:** Make the three architecture/hard-surface recipes create connected, parameterized, visible graph batches.

**Files:**
- Modify: `codex_plugin/blendex_mcp/recipes.py`
- Modify: `codex_plugin/blendex_mcp/catalog.py`
- Modify: `tests/codex_plugin/test_recipes.py`
- Modify: `tests/blender_addon/test_safety.py`
- Modify: `tests/blender_addon/test_batches.py`

### Task 0.33.1: Modular grid tower graph

- [ ] **Step 1: Write failing recipe graph test**

Assert `architecture.grid_tower` operations include parameterized labels or socket values for `levels` and `columns`, create a modifier, create multiple graph nodes, and link toward output.

- [ ] **Step 2: Verify RED**

Run recipe tests and confirm the grid tower test fails.

- [ ] **Step 3: Implement grid tower batch**

Use the graph DSL to generate a tower graph with deterministic client ids, links, and socket values derived from `levels` and `columns`.

- [ ] **Step 4: Verify GREEN**

Run recipe tests and safety dry-run tests.

### Task 0.33.2: Wall panel graph

- [ ] **Step 1: Write failing wall panel test**

Assert `segments` affects the generated graph and previewable socket values.

- [ ] **Step 2: Implement wall panel graph**

Use transform/join-style operations and labels that produce an inspectable connected graph.

- [ ] **Step 3: Run targeted tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_recipes tests.blender_addon.test_safety -v
```

### Task 0.33.3: Modular building graph

- [ ] **Step 1: Write failing modular building test**

Assert `floors` affects the batch and the recipe uses material or transform semantics when available.

- [ ] **Step 2: Implement modular building graph**

Use the graph DSL and semantic catalog entries for building-related nodes.

- [ ] **Step 3: Run full unit tests**

Run:

```bash
./scripts/run_unit_tests.sh
```

---

## Stage 0.34: Complete Scattering Recipes

**Purpose:** Make the three nature/scattering recipes create connected, parameterized graph batches with density, seed, and scale controls.

**Files:**
- Modify: `codex_plugin/blendex_mcp/recipes.py`
- Modify: `codex_plugin/blendex_mcp/catalog.py`
- Modify: `tests/codex_plugin/test_recipes.py`
- Modify: `tests/blender_addon/test_safety.py`
- Modify: `tests/blender_addon/test_batches.py`

### Task 0.34.1: Random stone scatter

- [ ] **Step 1: Write failing test**

Assert `density` and `seed` appear in socket value operations or parameter-driven labels, and the graph includes distribute points, instance on points, realize instances, and output links.

- [ ] **Step 2: Implement recipe graph**

Generate a connected scatter graph using deterministic client ids and capability-declared node types.

- [ ] **Step 3: Run targeted tests**

Run recipe, safety, and batch tests.

### Task 0.34.2: Ground point distribution

- [ ] **Step 1: Write failing test**

Assert density and seed affect the graph and preview.

- [ ] **Step 2: Implement recipe graph**

Generate a point-distribution graph with dry-run-visible socket values.

- [ ] **Step 3: Run targeted tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_recipes tests.blender_addon.test_safety -v
```

### Task 0.34.3: Simple grass scatter

- [ ] **Step 1: Write failing test**

Assert density and scale affect the graph and preview.

- [ ] **Step 2: Implement grass graph**

Generate a connected graph with distribute points, instance, realize, scale/transform values, and output link expectations.

- [ ] **Step 3: Run full tests**

Run:

```bash
./scripts/run_unit_tests.sh
```

---

## Stage 0.35: Planner Parameter Extraction and Capability Gating

**Purpose:** Make natural-language planning useful inside the supported v0.4 scope.

**Files:**
- Modify: `codex_plugin/blendex_mcp/planner.py`
- Modify: `tests/codex_plugin/test_planner.py`
- Modify: `codex_plugin/blendex_mcp/recipes.py`

### Task 0.35.1: Extract numeric parameters

- [ ] **Step 1: Write failing planner tests**

Add cases:

- `"make a 12 level grid tower with 6 columns"` extracts `levels=12`, `columns=6`.
- `"scatter stones density 45 seed 9"` extracts `density=45`, `seed=9`.
- `"grass scatter density 100 scale 1.5"` extracts `density=100`, `scale=1.5`.

- [ ] **Step 2: Verify RED**

Expected: FAIL because planner currently calls recipes with defaults.

- [ ] **Step 3: Implement deterministic extraction**

Add regex-based extraction helpers for integer and number parameters, clamped by recipe validation through `Recipe.normalize_params`.

- [ ] **Step 4: Verify GREEN**

Run planner and recipe tests.

### Task 0.35.2: Capability gating

- [ ] **Step 1: Write failing capability tests**

Pass capabilities missing `GeometryNodeInstanceOnPoints` and assert grass/stone plans return `PLANNER_UNSUPPORTED_REQUEST` with missing node details.

- [ ] **Step 2: Implement gating**

Before returning a recipe plan, compare recipe `required_node_types` to `capabilities["node_types"]` when capabilities are supplied.

- [ ] **Step 3: Run tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_planner -v
./scripts/run_unit_tests.sh
```

---

## Stage 0.36: Dry-Run, Confirmation, and Execution Summaries

**Purpose:** Make previews and summaries understandable for complete graph batches.

**Files:**
- Modify: `codex_plugin/blendex_mcp/workflow.py`
- Modify: `tests/codex_plugin/test_workflow.py`
- Modify: `blender_addon/blendex/safety.py`
- Modify: `tests/blender_addon/test_safety.py`
- Modify: `blender_addon/blendex/batches.py`
- Modify: `tests/blender_addon/test_batches.py`

### Task 0.36.1: Rich dry-run preview

- [ ] **Step 1: Write failing dry-run tests**

Assert dry-run preview includes object count, modifier count, node count, link count, socket value count, label count, warning count, and `undo_available` when all mutations are reversible.

- [ ] **Step 2: Implement preview additions**

Extend `dry_run_operations` to include a compact summary object while preserving existing arrays.

- [ ] **Step 3: Run safety tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_safety -v
```

### Task 0.36.2: Post-execution summary helper

- [ ] **Step 1: Write failing workflow tests**

Add tests for `execution_summary(batch_result, tree_result)` that names batch status, target, created nodes, links, socket values, and undo status.

- [ ] **Step 2: Implement helper**

Add summary helper in `workflow.py`.

- [ ] **Step 3: Run workflow tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_workflow -v
```

---

## Stage 0.37: Expanded Undo for Links and Socket Values

**Purpose:** Make recipe-generated full graphs reversible when every operation has a safe inverse.

**Files:**
- Modify: `blender_addon/blendex/batches.py`
- Modify: `blender_addon/blendex/executor.py`
- Modify: `tests/blender_addon/test_batches.py`
- Modify: `tests/blender_addon/test_executor_fake.py`

### Task 0.37.1: Undo created links

- [ ] **Step 1: Write failing tests**

Execute a batch that creates nodes and a link. Assert `undo_last_batch()` removes the link and created nodes.

- [ ] **Step 2: Implement link inverse recording**

Before `geometry_nodes.link_sockets`, record endpoints after reference resolution. After success, add an undo step that removes the created link.

- [ ] **Step 3: Run batch tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_batches -v
```

### Task 0.37.2: Undo socket value changes

- [ ] **Step 1: Write failing tests**

Create a socket with existing default value, execute `set_socket_value`, undo, and assert the previous default is restored.

- [ ] **Step 2: Implement socket value inverse**

Record previous default values before mutation and restore them during undo.

- [ ] **Step 3: Run executor and batch tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_executor_fake tests.blender_addon.test_batches -v
```

---

## Stage 0.38: Blender UI and Local Beta Packaging

**Purpose:** Make setup and local use practical for testers.

**Files:**
- Modify: `blender_addon/blendex/ui.py`
- Modify: `tests/blender_addon/test_ui.py`
- Create: `scripts/package_blender_addon.py`
- Modify: `tests/codex_plugin/test_version.py`
- Modify: `README.md`

### Task 0.38.1: Tester-friendly UI state

- [ ] **Step 1: Write failing UI tests**

Assert panel draw code shows full token or a copy instruction, last auth error, recent batch summary, and undo status text.

- [ ] **Step 2: Update UI panel**

Improve labels while keeping the panel lightweight.

- [ ] **Step 3: Run UI tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_ui -v
```

### Task 0.38.2: Add-on package helper

- [ ] **Step 1: Write failing script test**

Assert `scripts/package_blender_addon.py` exists and creates `dist/blendex-addon-<version>.zip`.

- [ ] **Step 2: Implement packaging script**

Zip `blender_addon/blendex` plus required protocol source files into a local beta artifact.

- [ ] **Step 3: Run packaging smoke**

Run:

```bash
PYTHONPATH=src:. python3 scripts/package_blender_addon.py
```

Expected: zip path is printed and file exists under `dist/`.

---

## Stage 0.39: Real Blender Smoke and Demo Prompt Flows

**Purpose:** Prove complete recipe behavior in real Blender when available and document demo flows.

**Files:**
- Modify: `tests/integration/blender_smoke.py`
- Modify: `scripts/run_blender_smoke.py`
- Create: `docs/demo-prompts.md`
- Modify: `README.md`

### Task 0.39.1: Architecture recipe smoke

- [ ] **Step 1: Write failing smoke assertions**

Extend smoke to build `architecture.grid_tower`, execute the confirmed batch, inspect the tree, and assert created labels and links are present.

- [ ] **Step 2: Implement smoke support**

Import the recipe registry in the smoke script and execute the batch through `execute_batch`.

- [ ] **Step 3: Run smoke**

Run:

```bash
python3 scripts/run_blender_smoke.py
```

Expected: PASS when `BLENDER` is configured or clear SKIP when not.

### Task 0.39.2: Scattering recipe smoke

- [ ] **Step 1: Write failing smoke assertions**

Add a scattering recipe path, preferably `scatter.stones`, with inspect-tree assertions.

- [ ] **Step 2: Implement smoke support**

Run the second recipe in the same background Blender session or a fresh object.

- [ ] **Step 3: Run smoke and unit tests**

Run:

```bash
python3 scripts/run_blender_smoke.py
./scripts/run_unit_tests.sh
```

### Task 0.39.3: Demo prompt docs

- [ ] **Step 1: Write docs test**

Assert `docs/demo-prompts.md` names all six built-in recipes and contains dry-run/confirm/inspect/undo flow.

- [ ] **Step 2: Create demo prompts**

Document copy-pasteable prompts and expected behavior for each recipe.

- [ ] **Step 3: Run docs tests**

Run the targeted test and release checks.

---

## Stage 0.40: Final Metadata, Release Docs, and Readiness Audit

**Purpose:** Align final v0.4 metadata, clean docs, run release checks, and prove completion requirement by requirement.

**Files:**
- Modify: `codex_plugin/blendex_mcp/version.py`
- Modify: `.codex-plugin/plugin.json`
- Modify: `pyproject.toml`
- Modify: `blender_addon/blendex/__init__.py`
- Modify: `README.md`
- Create: `docs/superpowers/reviews/2026-06-19-blendex-v0-4-readiness.md`
- Modify: `tests/codex_plugin/test_version.py`

### Task 0.40.1: Final version alignment

- [ ] **Step 1: Write failing final version test**

Assert `VERSION == "0.40.0"` and metadata files match.

- [ ] **Step 2: Update metadata**

Set final v0.4 version:

```python
VERSION = "0.40.0"
```

Set plugin, pyproject, and Blender `bl_info` to the same version.

- [ ] **Step 3: Run version tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_version -v
```

### Task 0.40.2: README finalization

- [ ] **Step 1: Write README release tests**

Assert README includes:

- v0.4 local beta status.
- Setup steps.
- Token steps.
- Six example prompts.
- Troubleshooting.
- Known limits.
- Release check command.

- [ ] **Step 2: Update README**

Make README the single practical entrypoint for testers.

- [ ] **Step 3: Run README tests**

Run targeted tests.

### Task 0.40.3: Readiness audit

- [ ] **Step 1: Create readiness evidence matrix**

Create `docs/superpowers/reviews/2026-06-19-blendex-v0-4-readiness.md` with each release criterion from the spec and a current evidence row:

- Requirement.
- Evidence file or command.
- Result.
- Residual risk.

- [ ] **Step 2: Run full verification**

Run:

```bash
./scripts/run_release_checks.sh
```

Expected: PASS; Blender smoke may skip only if `BLENDER` is unset and the readiness document records that limitation.

- [ ] **Step 3: Final completion decision**

Only mark v0.4 complete if the readiness audit proves every release criterion. If any evidence is missing, continue implementation rather than declaring completion.

---

## Completion Audit Checklist

Before calling the active goal complete, verify each item with current-state evidence:

- [ ] Design spec exists and matches the requested 0.4 objective.
- [ ] Implementation plan exists and covers 0.31 through 0.40.
- [ ] Version metadata reaches `0.40.0`.
- [ ] Six built-in recipes emit complete graph batches.
- [ ] Planner extracts parameters and gates by capabilities.
- [ ] Dry-run and confirmation summaries cover full graph changes.
- [ ] Batch execution records meaningful history.
- [ ] Undo covers supported full recipe batches or reports unavailable honestly.
- [ ] README is tester-ready and internally consistent.
- [ ] Packaging helper produces a local beta add-on artifact.
- [ ] Unit tests pass.
- [ ] MCP probe passes.
- [ ] Blender smoke passes with `BLENDER` configured or records a clear skip when unavailable.
- [ ] `git diff --check` passes.
- [ ] Readiness review maps every release criterion to evidence.
