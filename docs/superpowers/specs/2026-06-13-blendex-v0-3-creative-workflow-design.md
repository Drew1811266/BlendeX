# BlendeX v0.3 Creative Workflow Design Spec

Date: 2026-06-13

## Summary

BlendeX v0.3 should turn the v0.2 graph kernel into an early-user-ready AI-assisted procedural modeling workflow. The v0.2 release proved the split bridge: CodeX-side MCP tools can send structured requests, the Blender add-on can execute allowlisted Geometry Nodes operations, and the protocol can validate, dry-run, and report structured errors. The next major version should make that kernel feel useful in real creative work.

The chosen direction is a creative closed loop with trust controls as hard requirements:

1. The user describes a procedural modeling goal in CodeX.
2. BlendeX scans Blender runtime capabilities and scene state.
3. CodeX creates a structured plan, using a stable recipe when one matches or a semi-open planner when the request is outside a recipe.
4. BlendeX dry-runs the operation batch and summarizes the expected changes.
5. The user confirms before mutation.
6. Blender executes only allowlisted, BlendeX-owned mutations.
7. BlendeX records the batch, inspects the result, and supports retry or undo when needed.

v0.3 should not chase fully open-ended Blender automation. It should make architectural or hard-surface and nature or scattering workflows reliable enough that an early user can install the project, connect CodeX to Blender, create small procedural assets, understand failures, and undo BlendeX changes without fear.

## Approved Product Direction

The approved direction combines these decisions:

- Product emphasis: natural-language creation plus a trustworthy professional workflow.
- Natural-language mode: semi-open planning, with a few high-quality recipes as stable paths.
- Trust workflow: mutation confirmation and batch history or undo are part of the mainline, not polish.
- Recipe focus: architecture or hard-surface and nature or scattering.
- Primary interaction surface: CodeX App.
- Blender add-on role: reliable local executor, connection panel, token display, recent batch status, logs, and undo entry point.
- Completion standard: early-user-ready, with selected release-readiness practices such as version metadata alignment, real Blender smoke testing, and practical documentation.

## Goals

- Provide a natural-language-to-Geometry-Nodes workflow that can plan, preview, confirm, execute, inspect, retry, and undo BlendeX-owned changes.
- Add a recipe system for stable creative paths in architecture or hard-surface and nature or scattering scenarios.
- Add semi-open planning for requests that do not exactly match a recipe, while keeping dry-run and confirmation mandatory before mutation.
- Make the session token meaningful for local CodeX-to-Blender requests.
- Record batch history with enough information for audits, UI display, retry hints, and undo.
- Implement undo for the latest BlendeX mutation batch using a reliable, testable ownership boundary.
- Improve user-facing errors so failures explain what went wrong, whether the scene changed, and what the user or planner can try next.
- Keep Blender as the execution environment and CodeX as the planning and confirmation environment.
- Keep the project installable and testable by early users through clear local setup docs and smoke tests.

## Non-Goals

- v0.3 will not execute arbitrary AI-generated Python in Blender.
- v0.3 will not provide a full chat or planning UI inside Blender.
- v0.3 will not promise success for every possible Geometry Nodes idea.
- v0.3 will not mutate arbitrary user-owned complex node trees unless the user explicitly marks them as BlendeX-owned.
- v0.3 will not attempt a marketplace-grade plugin release.
- v0.3 will not build polished visual graph diff UI. It will return and display structured summaries that can support a future visual diff.
- v0.3 will not implement advanced asset libraries, material authoring systems, or photorealistic final rendering workflows.

## Current Baseline

The repository is at v0.2 graph kernel. It currently includes:

- Shared protocol request, response, error, and validation code in `src/blendex_protocol`.
- Blender add-on modules for state, UI, WebSocket service, main-thread dispatch, capability scanning, scene inspection, executor behavior, safety validation, and dry-run preview.
- CodeX-side MCP server, tool definitions, WebSocket client, and semantic Geometry Nodes catalog.
- v0.2 tools for capability scan, scene inspection, carrier mesh creation, modifier creation, tree inspection, node creation, socket value setting, socket linking, node labeling, batch validation, and dry-run.
- Unit tests for protocol, MCP server and client behavior, fake Blender runtime behavior, executor safety, scene inspection, and add-on import.
- A Blender background smoke test scaffold that runs when the `BLENDER` environment variable points to a local Blender executable.

Important gaps that v0.3 should close:

- The session token exists in Blender state but does not yet protect requests.
- The project can validate and dry-run batches, but it does not yet enforce a user confirmation workflow at the MCP planning level.
- Batch history is limited to recent operation logs and is not rich enough for undo or retry workflows.
- `safety.undo_last_batch` is allowlisted but not implemented.
- Recipes and semi-open natural-language planning do not exist yet.
- Early-user setup docs and version metadata are not fully aligned.

## User Experience

The primary 0.3 workflow should feel like this:

1. The user opens Blender, enables the BlendeX add-on, starts the local service, and sees a token plus connection status in the Blender sidebar.
2. The user asks CodeX to create a procedural asset, for example "create a modular grid tower on the selected object" or "make a ground patch with randomly scattered stones."
3. CodeX calls BlendeX tools to check connection, authenticate, inspect the scene, scan capabilities, and choose a target object or create a carrier mesh.
4. CodeX chooses a recipe when the request fits a stable recipe. Otherwise, it creates a semi-open plan using available node capabilities and semantic catalog hints.
5. CodeX calls dry-run and presents a concise confirmation summary: target object, modifier, nodes to create, socket values to change, links to add, ownership assumptions, warnings, and rollback availability.
6. The user confirms.
7. CodeX sends the approved batch for execution.
8. Blender executes the batch on the main thread, records a batch history entry, and returns a structured result.
9. CodeX inspects the tree after execution and summarizes what changed.
10. If the result is wrong or a step failed, the user can ask CodeX to retry with updated parameters or undo the last BlendeX batch.

## Architecture

v0.3 keeps the split bridge architecture:

```text
CodeX App
  |
  | MCP tools, planning, confirmation, recipes
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

The main architectural change is to add a creative workflow layer above the v0.2 graph kernel and a trust layer around it.

CodeX-side responsibilities:

- Connection and authentication checks.
- Recipe matching and parameter normalization.
- Semi-open planning for non-recipe requests.
- Batch construction.
- Dry-run orchestration.
- User-facing confirmation summaries.
- Retry planning after structured failures.
- Documentation for suggested user prompts and supported creative scopes.

Blender-side responsibilities:

- Token validation for local requests.
- Runtime capability and scene inspection.
- Allowlisted operation execution on the main thread.
- Batch history persistence for the active Blender session.
- Undo last BlendeX batch.
- Recent batch and error status for the sidebar panel.
- Structured error reporting with mutation-state clarity.

Shared protocol responsibilities:

- Explicit request and response shapes for authentication, confirmation, batch execution, batch history, undo, recipe metadata, and planner results where those cross the CodeX-to-Blender boundary.
- Stable error codes for auth failures, confirmation-required failures, partial execution, undo unavailable, recipe mismatch, planner unsupported, and batch recovery cases.
- Backward-compatible handling of existing v0.2 operations.

## Planning Modes

### Recipe Mode

Recipe mode should be used when the user request clearly matches a supported recipe. A recipe is a structured generator definition, not free-form Python. It defines:

- Recipe id.
- Human-readable label.
- Creative category.
- Supported target requirements.
- Parameters with types, defaults, ranges, and user-facing descriptions.
- Required node types or capability hints.
- Operation batch builder.
- Dry-run preview text.
- Validation rules.
- Example prompts.
- Test fixtures.

v0.3 recipe categories:

- Architecture or hard-surface:
  - Modular grid tower.
  - Procedural wall panel.
  - Simple modular building massing.
- Nature or scattering:
  - Random stone scatter.
  - Ground point distribution.
  - Simple grass scatter.

The recipe system should be extensible, but the v0.3 implementation should prioritize a small number of reliable recipes over a large catalog.

### Semi-Open Planner Mode

Semi-open planner mode should handle requests that do not exactly match a recipe but remain inside the Geometry Nodes graph kernel. It should:

- Inspect scene and capabilities before planning.
- Choose only node types reported by the active Blender runtime.
- Prefer BlendeX-owned targets or create a carrier mesh.
- Build operation batches using the existing structured operations.
- Dry-run before execution.
- Ask for confirmation before mutation.
- Degrade gracefully when a request is too broad or unsupported.

Semi-open planning may produce simpler results than the user's full artistic intent. Its success criterion is a coherent and inspectable graph mutation, not artistic perfection.

Unsupported requests should produce a useful response with one or more of:

- A supported recipe suggestion.
- Missing node or capability explanation.
- A safer smaller plan.
- A request for a narrower target.

## Trust and Safety Workflow

### Authentication

The Blender add-on already generates a session token. v0.3 should make that token part of request authentication. The CodeX-side client must send the token during the handshake or request envelope. The Blender server must reject missing or mismatched tokens with a structured `AUTH_REQUIRED` or `AUTH_FAILED` response.

Authentication should remain local and lightweight:

- Bind service to `127.0.0.1`.
- Keep the token visible in the Blender panel.
- Avoid storing credentials outside the local project unless the user explicitly configures it.
- Keep tests independent of real secrets.

### Confirmation

Mutating operations should be executed only after an explicit confirmation path. The default CodeX-side workflow should be:

1. Build an operation batch.
2. Call `blendex_dry_run`.
3. Present a confirmation summary.
4. Send the batch only after user approval.

The confirmation summary must include:

- Target object and modifier.
- Whether the target is BlendeX-owned.
- Nodes to create.
- Links to create.
- Socket values to change.
- Labels to set.
- Warnings.
- Undo availability.

Read-only operations such as inspect and scan do not require confirmation.

### Ownership

v0.3 keeps the v0.2 ownership rule:

- Mutation requires a BlendeX-owned modifier and node group unless the operation is explicitly designed to create or mark ownership.
- Read-only inspection of user-created objects and node trees is allowed.
- Planner and recipe paths should default to creating or reusing BlendeX-owned surfaces.

### Batch History

Each mutating batch should create a history entry with:

- Batch id.
- Created timestamp.
- Source tool or planner mode.
- User-facing summary.
- Target object and modifier.
- Requested operations.
- Dry-run preview snapshot.
- Execution result per operation.
- Whether the batch fully succeeded, partially succeeded, failed before mutation, or failed after partial mutation.
- Undo status.
- Retry hint when available.

The Blender panel should show recent batches in a compact form: status, target, operation count, and last error. CodeX tools should be able to query recent batch history.

### Undo

v0.3 should implement `safety.undo_last_batch` for BlendeX-owned mutation batches. The first implementation may use a conservative undo strategy, but it must be testable and honest about its limits.

Acceptable v0.3 behavior:

- Undo the latest executed BlendeX batch when the batch recorded enough state to reverse or when Blender's undo stack can be used safely.
- Return `UNDO_UNAVAILABLE` when no safe undo path exists.
- Never claim undo succeeded unless the scene state was changed back or Blender confirmed the undo.
- Update batch history after an undo attempt.

The implementation plan should decide whether to use explicit inverse operations, Blender undo push/pop behavior, or a hybrid. The design requirement is that the UI and tool responses make undo status clear.

## Error Handling

v0.3 should improve errors around creative workflows. Existing structured errors should remain, and new workflow errors should include:

- `AUTH_REQUIRED`: no token was provided.
- `AUTH_FAILED`: provided token did not match the active Blender session.
- `CONFIRMATION_REQUIRED`: a mutating batch was requested without an approved confirmation path.
- `RECIPE_NOT_FOUND`: no recipe matched the requested recipe id.
- `RECIPE_UNSUPPORTED_TARGET`: the recipe cannot run on the chosen target.
- `PLANNER_UNSUPPORTED_REQUEST`: the semi-open planner cannot produce a safe plan.
- `BATCH_PARTIALLY_APPLIED`: execution changed part of the scene before failing.
- `UNDO_UNAVAILABLE`: no safe undo is available for the requested batch.
- `BATCH_NOT_FOUND`: requested batch id is not in history.

Error responses should include:

- Machine-readable code.
- Human-readable message.
- Retry hint when a retry is realistic.
- Whether mutation occurred when the error happened during execution.
- Relevant target object, modifier, operation id, and batch id when known.

## Blender UI

The Blender panel should remain a status and control surface, not a full creative UI. v0.3 should add or refine:

- Service status.
- Client connection status.
- Session token display.
- Auth status when a client connects.
- Recent batch list.
- Last error summary.
- Undo last BlendeX batch button.
- A short indication when the add-on is waiting for CodeX confirmation or has just executed a batch.

The panel should avoid becoming a full recipe browser or chat interface in v0.3.

## CodeX Tool Surface

The exact implementation plan may refine tool names, but v0.3 should support these tool families:

- Connection and auth:
  - Authenticate or send token.
  - Check service status.
- Workflow planning:
  - List recipes.
  - Build recipe batch.
  - Build semi-open plan.
- Confirmation and execution:
  - Dry-run plan.
  - Execute confirmed batch.
- History and recovery:
  - List recent batches.
  - Inspect batch.
  - Undo last batch.

Existing v0.2 low-level graph tools should remain available for internal composition and advanced use.

## Version Roadmap

The 0.3 release should be split into ten small versions. Each small version should be independently testable and should leave the project in a usable state.

### 0.21: Version Metadata and Baseline Hygiene

Purpose: make the v0.2 baseline clean and prepare the repository for a multi-version 0.3 track.

Deliverables:

- Align `.codex-plugin/plugin.json`, `pyproject.toml`, Blender `bl_info`, README, and MCP server version reporting.
- Document the v0.2 baseline and v0.3 target in README.
- Confirm unit tests pass.
- Confirm the Blender smoke test command is documented and skips clearly when `BLENDER` is not configured.

Exit criteria:

- All project metadata agrees on the current development version.
- README explains that 0.3 is in progress and what v0.2 can already do.
- Unit tests pass.

### 0.22: Authenticated Local Session

Purpose: make the Blender session token enforce local request authentication.

Deliverables:

- Add token transport from CodeX MCP client to Blender server.
- Reject missing or invalid tokens with structured auth errors.
- Show auth status in Blender state and panel.
- Add tests for missing, invalid, and valid token paths.

Exit criteria:

- Mutating and read-only WebSocket requests require a valid active token unless explicitly running in a test bypass.
- Auth failures are visible to CodeX as tool errors.

### 0.23: Batch History and Audit Trail

Purpose: record creative workflow batches as first-class state.

Deliverables:

- Define batch history data structures.
- Record dry-run preview, execution result, status, target, operations, and timestamps.
- Add MCP tools or tool results for recent batch history.
- Show recent batches in the Blender panel.

Exit criteria:

- Every executed mutating batch has a batch id.
- The user can inspect recent batch outcomes from CodeX and Blender UI.

### 0.24: Undo Last Batch and Recovery Signals

Purpose: make BlendeX changes reversible when a safe path exists.

Deliverables:

- Implement `safety.undo_last_batch`.
- Track undo status per batch.
- Return clear errors for unavailable undo.
- Improve partial-failure reporting and retry hints.

Exit criteria:

- A successful test batch can be undone in fake runtime tests.
- Unsupported undo cases fail safely with `UNDO_UNAVAILABLE`.
- Batch history reflects undo attempts and outcomes.

### 0.25: Confirmation-First Execution Workflow

Purpose: enforce the planning contract before mutation.

Deliverables:

- Add a CodeX-side workflow helper for plan, dry-run, confirmation summary, and execution.
- Add confirmation metadata to batch execution.
- Reject unconfirmed mutating batches when the workflow requires confirmation.
- Improve dry-run summaries for user-facing confirmation.

Exit criteria:

- Normal creative workflows dry-run before execution.
- Mutating execution has explicit confirmation metadata.
- Read-only scan and inspect remain frictionless.

### 0.26: Recipe Infrastructure

Purpose: create a reusable structure for stable creative generators.

Deliverables:

- Define recipe schema and registry.
- Define recipe parameter validation.
- Implement recipe-to-operation-batch builders.
- Add recipe listing and recipe batch building tools.
- Add tests for parameter defaults, invalid parameters, missing capabilities, and generated operation shapes.

Exit criteria:

- CodeX can list available recipes and build a dry-runnable batch for a recipe.
- Recipe failures explain missing inputs or capabilities.

### 0.27: Architecture and Hard-Surface Recipes

Purpose: provide the first stable creative recipes.

Deliverables:

- Modular grid tower recipe.
- Procedural wall panel recipe.
- Simple modular building massing recipe.
- Example prompts and expected parameter sets.
- Tests for generated batch structure and dry-run previews.

Exit criteria:

- The architecture recipes produce inspectable BlendeX-owned Geometry Nodes graphs.
- Recipe parameters affect generated graph structure or socket values in predictable ways.

### 0.28: Nature and Scattering Recipes

Purpose: provide stable scatter-focused workflows.

Deliverables:

- Random stone scatter recipe.
- Ground point distribution recipe.
- Simple grass scatter recipe.
- Parameters for density, seed, scale range, and target area where supported.
- Tests for generated batch structure and dry-run previews.

Exit criteria:

- The scatter recipes produce inspectable BlendeX-owned Geometry Nodes graphs.
- Dry-run previews clearly describe object, modifier, node, link, and socket-value changes.

### 0.29: Semi-Open Natural-Language Planner

Purpose: support requests outside exact recipes without leaving the safe graph kernel.

Deliverables:

- Add planner primitives that map high-level intents to graph operations.
- Use runtime capability scan and semantic catalog data during planning.
- Prefer recipes when the request matches a supported recipe.
- Generate safe fallback plans or unsupported-request explanations.
- Add tests for recipe match, planner fallback, missing capability, and unsupported request behavior.

Exit criteria:

- A non-recipe request can produce a dry-runnable operation batch when it fits supported graph primitives.
- Unsupported requests return a useful explanation and suggested narrower alternatives.

### 0.30: Early-User Release Hardening

Purpose: make the 0.3 track coherent for early users.

Deliverables:

- Update README with installation, connection, token, confirmation, recipe, undo, and troubleshooting guides.
- Align release notes and version metadata for v0.3.
- Expand real Blender smoke tests where local Blender is available.
- Add demo scripts or documented prompt flows for the architecture and scattering workflows.
- Run full unit tests and documented smoke verification.

Exit criteria:

- A new early user can follow docs to install the add-on, connect CodeX, run a recipe, confirm execution, inspect the result, and undo it.
- All unit tests pass.
- The Blender smoke script either passes with `BLENDER` configured or clearly skips without masking failures.

## Testing Strategy

Each small version should add tests at the lowest reliable layer:

- Protocol validation tests for new request and response shapes.
- MCP server tests for tool schemas, argument validation, and error propagation.
- Fake Blender runtime tests for executor, auth, history, undo, and safety behavior.
- Recipe tests for parameter validation and operation batch output.
- Planner tests for matching, fallback, unsupported request handling, and capability constraints.
- Blender background smoke tests for the most important end-to-end path when a local Blender executable is available.

The final v0.3 verification should include:

- Full unit test suite.
- MCP initialize and tools/list smoke.
- At least one recipe workflow through dry-run and execution in fake runtime tests.
- At least one undo workflow in fake runtime tests.
- Blender background smoke for create modifier, create nodes, inspect tree, and at least one 0.3 workflow when Blender is configured.

## Documentation Strategy

v0.3 documentation should serve early users rather than only developers. It should include:

- What BlendeX can and cannot do in v0.3.
- Blender add-on setup from source.
- CodeX plugin setup.
- How to start the service and copy the token.
- How confirmation works.
- How recipe workflows work.
- How undo works and when it may be unavailable.
- Troubleshooting for connection, auth, missing node types, unsupported requests, and partial failures.
- Example prompts for architecture and scattering.

## Release Criteria

BlendeX v0.3 is complete when:

- The user can run at least one architecture or hard-surface recipe and one nature or scattering recipe through the full plan, dry-run, confirm, execute, inspect, and undo loop.
- Semi-open planning can safely handle a small set of non-recipe procedural modeling requests or explain why a request is unsupported.
- Session token authentication is enforced.
- Batch history is visible and queryable.
- Undo last batch is implemented with clear success or unavailable states.
- Mutating workflow requires confirmation by default.
- README and release docs explain setup and early-user workflows.
- Tests cover the new workflow boundaries.
- The final v0.3 metadata is aligned across plugin, package, Blender add-on, and MCP server.
