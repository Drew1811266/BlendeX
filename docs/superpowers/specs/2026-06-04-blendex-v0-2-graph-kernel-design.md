# BlendeX v0.2 Graph Kernel Design Spec

Date: 2026-06-04

## Summary

BlendeX v0.2 should turn the current MVP bridge into a usable Geometry Nodes graph editing kernel. The current project already has a safe split architecture, a Blender add-on WebSocket service, a CodeX-side MCP server, basic capability scanning, scene inspection, node creation, ownership checks, and tests. The next version should deepen the bridge rather than jump to high-level content generators.

The goal is for CodeX to understand enough of the active Blender scene, Geometry Nodes node tree, node sockets, supported operations, and BlendeX ownership state to create small valid node graphs through structured operations. v0.2 should make CodeX better at planning with Blender's real runtime constraints while preserving the project's core safety rule: no arbitrary AI-generated Python execution.

## Goals

- Let CodeX create or reuse a safe BlendeX-owned Geometry Nodes workspace on a selected object or new carrier mesh.
- Let CodeX inspect scene, modifier, node group, node, socket, link, selection, and ownership context before mutating anything.
- Extend runtime capability scanning from node type names to socket-aware node metadata where Blender exposes it.
- Add graph mutation operations for creating modifiers, setting socket values, linking sockets, labeling nodes, and marking BlendeX ownership.
- Add lightweight batch validation and dry-run preview so CodeX can reason about likely failures before execution.
- Merge runtime capabilities with a richer semantic catalog so CodeX receives both factual API availability and human-useful Geometry Nodes guidance.
- Keep all mutations allowlisted, observable, main-thread-dispatched, and constrained to BlendeX-owned graph surfaces unless explicitly read-only.

## Non-Goals

- v0.2 will not implement unrestricted Blender Python execution.
- v0.2 will not perform broad refactors of arbitrary user-created Geometry Nodes graphs.
- v0.2 will not prioritize polished high-level generators for forests, cities, products, terrain, or architecture.
- v0.2 will not add a natural language chat UI inside Blender.
- v0.2 will not require a full visual graph diff system. It should return structured previews that can support a visual diff later.
- v0.2 will not solve marketplace packaging unless a small manifest or README update is needed to expose the new MCP tools.

## Chosen Approach

Use an incremental Graph Kernel approach. This builds directly on the existing low-level operation protocol and fills in operations that are already present in the allowlist but not implemented. The version should move from "create one node" to "create and inspect a small connected node graph."

This approach is preferred over high-level recipes because recipes would be brittle without socket-aware capabilities, link validation, and richer inspect responses. It is also preferred over productization-first work because the current product surface is still too thin: CodeX needs a stronger Blender mental model before packaging polish pays off.

## Current Baseline

The current implementation already has:

- Shared protocol messages, errors, allowlisted operation names, and request validation in `src/blendex_protocol`.
- Blender add-on state, UI panel, logs, capability scanning, WebSocket service, and main-thread dispatch in `blender_addon/blendex`.
- A `GeometryNodesExecutor` that supports `geometry_nodes.create_node` and `geometry_nodes.inspect_tree`.
- A CodeX-side MCP server with `blendex_scan_capabilities`, `blendex_inspect_scene`, and `blendex_create_node`.
- A small semantic node catalog seed for common Geometry Nodes concepts.
- Unit tests for protocol, MCP mapping, WebSocket framing, dispatch, fake executor behavior, UI import behavior, and Blender smoke test scaffolding.

The current gap is not the transport. The gap is Blender understanding: node sockets, linkability, default values, modifier setup, ownership metadata, and machine-readable graph context are still minimal.

## Architecture

v0.2 keeps the Split Bridge architecture:

```text
CodeX App
  |
  | MCP tools
  v
CodeX BlendeX plugin
  |
  | local WebSocket / structured protocol
  v
Blender BlendeX add-on
  |
  | main-thread guarded bpy / Geometry Nodes operations
  v
Blender scene and Geometry Nodes node trees
```

The main architectural change is to introduce a clearer graph kernel boundary in the Blender add-on:

- Protocol validation defines the shape and invariants of structured operations.
- Capability scanning reports what the local Blender runtime can actually do.
- Scene and tree inspection report what is currently present.
- The Geometry Nodes executor applies only validated graph mutations.
- Safety preview validates batches without committing mutations where practical.
- The CodeX plugin maps MCP tools into protocol operations and enriches runtime data with semantic guidance.

The executor remains the only module allowed to mutate Blender data.

## Protocol and Tool Surface

v0.2 should expose these CodeX-side tools:

- `blendex_scan_capabilities`
  - Existing tool, extended result.
  - Returns Blender version, supported BlendeX operations, node types, socket templates where available, value type hints, and semantic catalog matches.

- `blendex_inspect_scene`
  - Existing tool, extended result.
  - Returns objects, object types, selected objects, active object, modifiers, Geometry Nodes modifiers, BlendeX ownership flags, node group names, and enough IDs to target follow-up operations.

- `blendex_create_carrier_mesh`
  - Creates a simple mesh object intended to host a procedural Geometry Nodes graph.
  - Returns `object_id`, object name, and selection state.

- `blendex_create_modifier`
  - Creates a Geometry Nodes modifier on a target object.
  - Marks the modifier and node group as BlendeX-owned by default.
  - Returns `object_id`, `modifier_id`, `node_group_id`, and ownership metadata.

- `blendex_inspect_tree`
  - Returns node tree structure for a target object's Geometry Nodes modifier.
  - Includes nodes, labels, locations, node types, input sockets, output sockets, socket identifiers, socket value previews, links, and ownership metadata.

- `blendex_create_node`
  - Existing tool, extended arguments.
  - Accepts `location` and optional structured label.
  - Returns node ID, socket summaries, label, and location.

- `blendex_set_socket_value`
  - Sets a writable input socket default value on a node.
  - Validates socket existence, direction, writable state, and value type before mutation.

- `blendex_link_sockets`
  - Creates a link from an output socket to an input socket.
  - Validates node IDs, socket IDs or names, socket direction, existing link constraints, and basic type compatibility.

- `blendex_label_node`
  - Sets a node label for graph readability.
  - Requires BlendeX ownership of the target modifier.

- `blendex_validate_batch`
  - Validates a list of structured operations and returns a plan with pass/fail entries.
  - Does not mutate Blender data.

- `blendex_dry_run`
  - Produces a structured preview for a batch, including target object, target modifier, expected created nodes, expected links, and warnings.
  - May share most validation logic with `blendex_validate_batch`.

Undo support should remain in the protocol allowlist but is not required for v0.2 unless it can be implemented cheaply with Blender's existing undo operator in a reliable testable way.

## Blender Runtime Understanding

The capability scanner should become socket-aware. For each available Geometry Nodes node type, the scanner should report:

- Node type identifier.
- Display name when available.
- Input socket templates when available.
- Output socket templates when available.
- Socket names.
- Socket identifiers when available.
- Socket data type or socket class name.
- Default value shape when available.
- Whether the node appears in the semantic catalog.
- Semantic role, common uses, and planning hints from the CodeX-side catalog when available.

Blender's Python API changes across versions, so the scanner must be defensive. If template APIs or socket metadata are unavailable for a node type, the scanner should still include the node type with empty or partial socket metadata and a `metadata_complete: false` style flag.

The scanner must report actual local availability first. Semantic catalog entries must never cause CodeX to believe a node exists when Blender did not report it.

## Scene and Tree Inspection

Scene inspection should return enough information for CodeX to decide where to work:

- Blender version.
- Objects with stable target IDs, names, object types, visibility where available, and selection state.
- Active object and selected objects.
- Modifiers per object, including modifier name, type, BlendeX ownership, and Geometry Nodes node group name.
- Whether each Geometry Nodes modifier is safe for mutation.
- A recommended target when possible:
  - selected object with BlendeX-owned Geometry Nodes modifier,
  - selected editable object with no Geometry Nodes modifier,
  - or no recommendation if ambiguous.

Tree inspection should return enough information for CodeX to reason about current graph shape:

- Modifier and node group metadata.
- Node IDs, names, labels, type identifiers, locations, dimensions when available.
- Input and output socket summaries.
- Link summaries with from-node, from-socket, to-node, and to-socket references.
- BlendeX ownership metadata.

Read-only inspection of user-created node trees is allowed. Mutation remains restricted to BlendeX-owned modifiers or node groups.

## Graph Mutation Rules

Graph mutations must follow these rules:

- Every mutation operation must validate `target.object_id`.
- Modifier mutation must validate modifier existence, type, and ownership where required.
- New BlendeX modifiers should set ownership metadata on both modifier and node group when possible.
- Node creation must validate node type availability from runtime capabilities.
- Socket value setting must validate that the target node and input socket exist.
- Socket value setting must reject incompatible values with `VALUE_TYPE_MISMATCH`.
- Linking must validate source node, source output socket, destination node, destination input socket, and basic socket compatibility.
- Linking must reject invalid links with `LINK_NOT_ALLOWED` or `SOCKET_TYPE_MISMATCH`.
- Operations should return created or modified identifiers so CodeX can chain follow-up operations without guessing Blender-generated names.

Where Blender exposes generated names rather than stable IDs, v0.2 should consistently use those names as operation IDs and document that they are Blender-local identifiers.

## Batch Validation and Dry Run

Batch validation should be lightweight and practical:

- Accept a list of structured operations.
- Validate operation names, required target fields, required params, ownership requirements, node type availability, socket names, and obvious link compatibility.
- Simulate created IDs within the batch when possible so a dry run can validate links to nodes created earlier in the same batch.
- Return a per-operation result with status, message, error code, retry hint, and operation index.
- Return aggregate status: `valid`, `invalid`, or `partial`.

Dry run should return a human- and machine-readable preview:

- Target object.
- Target modifier.
- Nodes expected to be created.
- Socket values expected to be changed.
- Links expected to be created.
- Warnings about incomplete runtime metadata or ambiguous socket references.

Dry run should not mutate Blender data.

## Semantic Catalog

The CodeX-side semantic catalog should expand from a small seed into a planning aid. It should include entries for common graph-building concepts:

- Group input and group output.
- Join geometry.
- Set position.
- Transform geometry.
- Instance on points.
- Realize instances.
- Distribute points on faces.
- Mesh primitives commonly used as instances.
- Set material.
- Store named attribute or capture attribute where available.
- Random value.
- Math and vector math helpers.

Each entry should include:

- Node type identifier.
- Role.
- Common use.
- Typical input sockets.
- Typical output sockets.
- Planning hints.
- Common pairing nodes.

The catalog should be merged with runtime scanning only for nodes that are actually available.

## Safety and Security

v0.2 keeps the existing safety posture:

- No arbitrary Python execution.
- WebSocket service remains bound to `127.0.0.1`.
- Blender API operations continue through main-thread dispatch.
- Mutations require allowlisted operation types.
- Mutations require BlendeX ownership unless the operation is explicitly read-only.
- Operation errors remain structured and tool-visible.

The existing session token in add-on state should become meaningful if it can be wired without expanding scope too much. If implemented in v0.2, the MCP client should send a token during WebSocket handshake or first request, and the Blender server should reject missing or mismatched tokens with `AUTH_REQUIRED`. If token wiring threatens the graph kernel scope, it should be deferred to v0.3 and documented in README as a known safety improvement.

## Error Handling

v0.2 should keep the existing `BlendexError` shape:

- `code`
- `message`
- `retry_hint`
- optional `details`

Graph operations should use existing error codes where possible:

- `OBJECT_NOT_FOUND`
- `OBJECT_NOT_SELECTED`
- `MODIFIER_NOT_FOUND`
- `NODE_TREE_NOT_FOUND`
- `NODE_TYPE_NOT_FOUND`
- `SOCKET_NOT_FOUND`
- `SOCKET_TYPE_MISMATCH`
- `LINK_NOT_ALLOWED`
- `VALUE_TYPE_MISMATCH`
- `OWNERSHIP_REQUIRED`
- `VALIDATION_FAILED`
- `EXECUTION_FAILED`

Error messages should be written for both CodeX recovery and human debugging.

## Testing Strategy

### Unit Tests

Add or extend tests for:

- Protocol validation for new operation payloads.
- MCP tool schemas and tool-to-operation mapping.
- Capability scanner socket metadata with fake Blender node classes.
- Scene inspection result shape with fake objects and modifiers.
- Executor creation of a Geometry Nodes modifier on fake Blender-like objects.
- Executor ownership marking.
- Node creation response with socket summaries.
- Socket value validation and mutation.
- Link validation and mutation.
- Batch validation and dry-run preview behavior.
- Error codes and retry hints for invalid node, socket, link, value, modifier, and ownership cases.

### Blender Smoke Test

When a Blender executable is available, the smoke test should verify:

- Add-on loads.
- A carrier mesh can be created or selected.
- A BlendeX-owned Geometry Nodes modifier can be created.
- Runtime capabilities return at least node type names and supported operations.
- A small graph can be created with at least two nodes.
- A socket value can be set on a node that supports a simple default value.
- A compatible link can be created.
- Tree inspection returns the created nodes and link.

### Manual Acceptance Test

A user can:

1. Open Blender and start the BlendeX service.
2. Ask CodeX to inspect the scene.
3. If no safe target exists, ask CodeX to create a carrier mesh and Geometry Nodes modifier.
4. Ask CodeX to build a tiny procedural graph using available nodes.
5. See nodes, links, labels, and socket values in Blender's Geometry Nodes editor.
6. Ask CodeX to inspect the tree and explain the graph it created.
7. See structured failures and retry hints when a node, socket, value, or link is invalid.

## Acceptance Criteria

v0.2 is complete when:

- CodeX has MCP tools for scene inspection, capability scanning, modifier setup, tree inspection, node creation, socket values, socket linking, labels, batch validation, and dry-run preview.
- Blender add-on implements the corresponding structured operations without arbitrary Python execution.
- Capability scanning includes socket-aware metadata where available and graceful partial metadata where unavailable.
- Scene and tree inspection return enough context for CodeX to target follow-up operations without guessing.
- Mutations are limited to BlendeX-owned graph surfaces.
- Unit tests pass.
- Blender smoke test passes when `BLENDER` points to a local Blender executable, or skips cleanly when unset.
- README documents the v0.2 tool surface and the local development verification flow.

## Future Extensions

After v0.2, the project can safely move toward:

- v0.3 high-level procedural recipes built on the graph kernel.
- Visual graph diff and confirmation UI.
- Reliable undo batches.
- Session token enforcement and stronger local auth.
- Packaged Blender add-on installation.
- More complete semantic catalogs for architecture, terrain, products, scattering, procedural materials, animation, and rendering workflows.
