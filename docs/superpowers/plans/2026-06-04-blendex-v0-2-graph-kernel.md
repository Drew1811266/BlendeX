# BlendeX v0.2 Graph Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the BlendeX v0.2 graph kernel so CodeX can inspect Blender scene context, understand Geometry Nodes sockets, create a BlendeX-owned graph surface, set socket values, link sockets, label nodes, and preview batches through structured operations.

**Architecture:** Keep the existing Split Bridge architecture. Extend the shared protocol and CodeX MCP tool registry first, then deepen Blender-side runtime inspection and executor operations while keeping every mutation allowlisted, main-thread-dispatched, and constrained to BlendeX-owned Geometry Nodes surfaces.

**Tech Stack:** Python 3.9+, Blender `bpy`, stdlib `unittest`, stdlib `socket`/`threading`, stdio MCP server, existing BlendeX protocol package.

---

## Scope

This plan implements `docs/superpowers/specs/2026-06-04-blendex-v0-2-graph-kernel-design.md`.

It includes:

- New MCP tools for carrier mesh creation, modifier creation, tree inspection, socket value setting, socket linking, node labeling, batch validation, and dry-run preview.
- Operation-specific protocol validation for the v0.2 graph surface.
- Socket-aware capability data with semantic catalog enrichment.
- Richer scene and tree inspection.
- Executor support for modifier setup and graph mutation.
- Lightweight batch validation and dry-run preview.
- Unit tests and Blender smoke test expansion.
- README updates for the v0.2 tool surface and verification flow.

It intentionally excludes:

- Arbitrary Python execution.
- High-level procedural generators.
- Full undo batches.
- Visual graph diff UI.
- Marketplace packaging.

## File Structure

- `src/blendex_protocol/validation.py`: operation allowlist and required-field/type validation for v0.2 payloads.
- `blender_addon/blendex/capabilities.py`: runtime node/socket capability scanning and supported operation reporting.
- `blender_addon/blendex/scene.py`: new scene inspection and carrier mesh helpers, extracted from `server.py`.
- `blender_addon/blendex/executor.py`: Geometry Nodes modifier, node, socket, link, label, ownership, inspect, and validation behavior.
- `blender_addon/blendex/safety.py`: new batch validation and dry-run preview helpers.
- `blender_addon/blendex/server.py`: dispatch routing for scene, graph, and safety operations.
- `codex_plugin/blendex_mcp/catalog.py`: expanded semantic node catalog plus merge helper.
- `codex_plugin/blendex_mcp/tools.py`: v0.2 MCP tool schemas and operation mapping.
- `codex_plugin/blendex_mcp/server.py`: stricter recursive argument validation for new tool schemas.
- `tests/protocol/test_validation.py`: protocol validation coverage for v0.2 operations.
- `tests/blender_addon/test_capabilities_fake.py`: socket-aware capability scanner tests.
- `tests/blender_addon/test_scene.py`: new fake scene inspection and carrier tests.
- `tests/blender_addon/test_executor_fake.py`: graph setup and mutation executor tests.
- `tests/blender_addon/test_safety.py`: batch validation and dry-run tests.
- `tests/blender_addon/test_server_dispatch.py`: dispatch routing tests for new operation families.
- `tests/codex_plugin/test_tools.py`: MCP tool mapping tests.
- `tests/codex_plugin/test_server.py`: MCP argument validation tests.
- `tests/integration/blender_smoke.py`: expanded Blender background smoke test.
- `README.md`: v0.2 tool surface and verification docs.

---

### Task 1: Protocol Validation for v0.2 Operations

**Files:**
- Modify: `src/blendex_protocol/validation.py`
- Modify: `tests/protocol/test_validation.py`

- [ ] **Step 1: Add failing validation tests**

Append these tests to `tests/protocol/test_validation.py` inside `ValidationTests`:

```python
    def test_accepts_create_modifier_request(self):
        request = OperationRequest(
            id="req_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": "BlendeX Geometry"},
        )

        validate_request(request)

    def test_accepts_link_sockets_request(self):
        request = OperationRequest(
            id="req_link",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": "Group Input",
                "from_socket": "Geometry",
                "to_node": "Group Output",
                "to_socket": "Geometry",
            },
        )

        validate_request(request)

    def test_rejects_link_sockets_missing_endpoint(self):
        request = OperationRequest(
            id="req_link_bad",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube"},
            params={"from_node": "A", "from_socket": "Geometry", "to_node": "B"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_set_socket_value_request(self):
        request = OperationRequest(
            id="req_value",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_id": "Value", "socket": "Value", "value": 2.5},
        )

        validate_request(request)

    def test_rejects_set_socket_value_missing_value_key(self):
        request = OperationRequest(
            id="req_value_bad",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube"},
            params={"node_id": "Value", "socket": "Value"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_batch_validation_request(self):
        request = OperationRequest(
            id="req_batch",
            type="safety.validate_batch",
            target={},
            params={
                "operations": [
                    {
                        "id": "op_1",
                        "type": "scene.inspect",
                        "target": {},
                        "params": {},
                    }
                ]
            },
        )

        validate_request(request)

    def test_rejects_batch_validation_without_operations_array(self):
        request = OperationRequest(
            id="req_batch_bad",
            type="safety.validate_batch",
            target={},
            params={"operations": "not a list"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.protocol.test_validation -v
```

Expected: FAIL because operation-specific validators for link sockets, socket values, and batch params are missing.

- [ ] **Step 3: Add helper validators**

Modify `src/blendex_protocol/validation.py` by adding these helpers above `validate_request`:

```python
def _require_string(mapping, key: str, message: str) -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise BlendexError("VALIDATION_FAILED", message)


def _require_value_key(mapping, key: str, message: str) -> None:
    if key not in mapping:
        raise BlendexError("VALIDATION_FAILED", message)


def _require_operations(params) -> None:
    operations = params.get("operations")
    if not isinstance(operations, list):
        raise BlendexError("VALIDATION_FAILED", "Batch operations must be an array.")
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise BlendexError(
                "VALIDATION_FAILED",
                f"Batch operation at index {index} must be an object.",
            )
```

- [ ] **Step 4: Add operation-specific validation branches**

Extend `validate_request` in `src/blendex_protocol/validation.py` with these branches after the existing `geometry_nodes.create_node` branch:

```python
    if request.type == "geometry_nodes.link_sockets":
        _require_string(request.params, "from_node", "link_sockets requires params.from_node.")
        _require_string(request.params, "from_socket", "link_sockets requires params.from_socket.")
        _require_string(request.params, "to_node", "link_sockets requires params.to_node.")
        _require_string(request.params, "to_socket", "link_sockets requires params.to_socket.")
    if request.type == "geometry_nodes.set_socket_value":
        _require_string(request.params, "node_id", "set_socket_value requires params.node_id.")
        _require_string(request.params, "socket", "set_socket_value requires params.socket.")
        _require_value_key(request.params, "value", "set_socket_value requires params.value.")
    if request.type == "geometry_nodes.label_node":
        _require_string(request.params, "node_id", "label_node requires params.node_id.")
        _require_string(request.params, "label", "label_node requires params.label.")
    if request.type == "geometry_nodes.mark_ownership":
        _require_string(request.target, "object_id", "mark_ownership requires target.object_id.")
    if request.type in {"safety.validate_batch", "safety.dry_run"}:
        _require_operations(request.params)
```

Keep the existing geometry operation `target.object_id` guard.

- [ ] **Step 5: Run validation tests**

Run:

```bash
python3 -m unittest tests.protocol.test_validation -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/blendex_protocol/validation.py tests/protocol/test_validation.py
git commit -m "feat: validate BlendeX v0.2 operations"
```

---

### Task 2: CodeX MCP Tool Surface

**Files:**
- Modify: `codex_plugin/blendex_mcp/tools.py`
- Modify: `codex_plugin/blendex_mcp/server.py`
- Modify: `tests/codex_plugin/test_tools.py`
- Modify: `tests/codex_plugin/test_server.py`

- [ ] **Step 1: Add failing MCP tool mapping tests**

Append these tests to `tests/codex_plugin/test_tools.py` inside `ToolMappingTests`:

```python
    def test_tool_names_include_v0_2_graph_kernel_tools(self):
        names = tool_names()

        for name in [
            "blendex_create_carrier_mesh",
            "blendex_create_modifier",
            "blendex_inspect_tree",
            "blendex_set_socket_value",
            "blendex_link_sockets",
            "blendex_label_node",
            "blendex_validate_batch",
            "blendex_dry_run",
        ]:
            self.assertIn(name, names)

    def test_create_modifier_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_create_modifier",
            {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            request_id="req_modifier",
        )

        self.assertEqual(operation["type"], "geometry_nodes.create_modifier")
        self.assertEqual(operation["target"]["object_id"], "Cube")
        self.assertEqual(operation["params"]["modifier_id"], "BlendeX Geometry")

    def test_set_socket_value_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_set_socket_value",
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "node_id": "Value",
                "socket": "Value",
                "value": 3.0,
            },
            request_id="req_value",
        )

        self.assertEqual(operation["type"], "geometry_nodes.set_socket_value")
        self.assertEqual(operation["params"]["value"], 3.0)

    def test_link_sockets_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_link_sockets",
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "from_node": "Group Input",
                "from_socket": "Geometry",
                "to_node": "Group Output",
                "to_socket": "Geometry",
            },
            request_id="req_link",
        )

        self.assertEqual(operation["type"], "geometry_nodes.link_sockets")
        self.assertEqual(operation["params"]["to_socket"], "Geometry")

    def test_validate_batch_maps_operations_array(self):
        operation = tool_to_operation(
            "blendex_validate_batch",
            {"operations": [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}]},
            request_id="req_batch",
        )

        self.assertEqual(operation["type"], "safety.validate_batch")
        self.assertEqual(operation["params"]["operations"][0]["type"], "scene.inspect")
```

- [ ] **Step 2: Add failing MCP server argument validation tests**

Append this test to `tests/codex_plugin/test_server.py` inside `ServerTests`:

```python
    def test_tools_call_rejects_invalid_v0_2_arguments(self):
        invalid_calls = [
            {"name": "blendex_create_modifier", "arguments": {"object_id": 3}},
            {"name": "blendex_link_sockets", "arguments": {"object_id": "Cube"}},
            {
                "name": "blendex_set_socket_value",
                "arguments": {"object_id": "Cube", "node_id": "Value", "socket": "Value"},
            },
            {"name": "blendex_validate_batch", "arguments": {"operations": "not a list"}},
        ]

        for params in invalid_calls:
            with self.subTest(params=params):
                response = server.handle_message(
                    {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": params},
                    FakeClient(),
                )
                self.assertEqual(response["error"]["code"], -32602)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_tools tests.codex_plugin.test_server -v
```

Expected: FAIL because the v0.2 tools and validation are not registered.

- [ ] **Step 4: Add reusable schema fragments**

In `codex_plugin/blendex_mcp/tools.py`, add these helpers above `TOOL_DEFINITIONS`:

```python
STRING_PROP = {"type": "string"}
NUMBER_PROP = {"type": "number"}
JSON_VALUE_PROP = {
    "oneOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {"type": "array"},
        {"type": "object"},
        {"type": "null"},
    ]
}
OPERATION_ARRAY_PROP = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": STRING_PROP,
            "type": STRING_PROP,
            "target": {"type": "object"},
            "params": {"type": "object"},
        },
        "required": ["id", "type"],
        "additionalProperties": True,
    },
}
```

- [ ] **Step 5: Extend `TOOL_DEFINITIONS`**

Add these tool entries to `TOOL_DEFINITIONS` after `blendex_create_node`:

```python
    {
        "name": "blendex_create_carrier_mesh",
        "description": "Create a simple mesh object for hosting a BlendeX Geometry Nodes graph.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": STRING_PROP},
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_create_modifier",
        "description": "Create a BlendeX-owned Geometry Nodes modifier on a target object.",
        "inputSchema": {
            "type": "object",
            "properties": {"object_id": STRING_PROP, "modifier_id": STRING_PROP},
            "required": ["object_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_inspect_tree",
        "description": "Inspect a Geometry Nodes tree on a target object and modifier.",
        "inputSchema": {
            "type": "object",
            "properties": {"object_id": STRING_PROP, "modifier_id": STRING_PROP},
            "required": ["object_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_set_socket_value",
        "description": "Set a writable input socket default value on a node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "node_id": STRING_PROP,
                "socket": STRING_PROP,
                "value": JSON_VALUE_PROP,
            },
            "required": ["object_id", "node_id", "socket", "value"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_link_sockets",
        "description": "Create a Geometry Nodes link from an output socket to an input socket.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "from_node": STRING_PROP,
                "from_socket": STRING_PROP,
                "to_node": STRING_PROP,
                "to_socket": STRING_PROP,
            },
            "required": ["object_id", "from_node", "from_socket", "to_node", "to_socket"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_label_node",
        "description": "Set a readable label on a node in a BlendeX-owned Geometry Nodes modifier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "node_id": STRING_PROP,
                "label": STRING_PROP,
            },
            "required": ["object_id", "node_id", "label"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_validate_batch",
        "description": "Validate a list of structured BlendeX operations without mutating Blender.",
        "inputSchema": {
            "type": "object",
            "properties": {"operations": OPERATION_ARRAY_PROP},
            "required": ["operations"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_dry_run",
        "description": "Preview a list of structured BlendeX operations without mutating Blender.",
        "inputSchema": {
            "type": "object",
            "properties": {"operations": OPERATION_ARRAY_PROP},
            "required": ["operations"],
            "additionalProperties": False,
        },
    },
```

- [ ] **Step 6: Extend tool mapping**

Add these branches to `tool_to_operation` before the final `ValueError`:

```python
    if name == "blendex_create_carrier_mesh":
        return {
            "id": request_id,
            "type": "scene.create_carrier_mesh",
            "target": {},
            "params": {"name": arguments.get("name", "BlendeX Carrier")},
        }
    if name == "blendex_create_modifier":
        return {
            "id": request_id,
            "type": "geometry_nodes.create_modifier",
            "target": {"object_id": arguments["object_id"]},
            "params": {"modifier_id": arguments.get("modifier_id", "BlendeX Geometry")},
        }
    if name == "blendex_inspect_tree":
        return {
            "id": request_id,
            "type": "geometry_nodes.inspect_tree",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {},
        }
    if name == "blendex_set_socket_value":
        return {
            "id": request_id,
            "type": "geometry_nodes.set_socket_value",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {
                "node_id": arguments["node_id"],
                "socket": arguments["socket"],
                "value": arguments["value"],
            },
        }
    if name == "blendex_link_sockets":
        return {
            "id": request_id,
            "type": "geometry_nodes.link_sockets",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {
                "from_node": arguments["from_node"],
                "from_socket": arguments["from_socket"],
                "to_node": arguments["to_node"],
                "to_socket": arguments["to_socket"],
            },
        }
    if name == "blendex_label_node":
        return {
            "id": request_id,
            "type": "geometry_nodes.label_node",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {"node_id": arguments["node_id"], "label": arguments["label"]},
        }
    if name == "blendex_validate_batch":
        return {
            "id": request_id,
            "type": "safety.validate_batch",
            "target": {},
            "params": {"operations": arguments["operations"]},
        }
    if name == "blendex_dry_run":
        return {
            "id": request_id,
            "type": "safety.dry_run",
            "target": {},
            "params": {"operations": arguments["operations"]},
        }
```

Also update the existing `blendex_create_node` mapping to include optional `location` and `client_id`:

```python
            "params": {
                "node_type": arguments["node_type"],
                "label": arguments.get("label", arguments["node_type"]),
                **({"location": arguments["location"]} if "location" in arguments else {}),
                **({"client_id": arguments["client_id"]} if "client_id" in arguments else {}),
            },
```

Add `location` and `client_id` to the `blendex_create_node` schema:

```python
                "location": {"type": "array", "items": NUMBER_PROP, "minItems": 2, "maxItems": 2},
                "client_id": STRING_PROP,
```

- [ ] **Step 7: Replace ad hoc MCP argument validation**

In `codex_plugin/blendex_mcp/server.py`, replace `_validate_tool_arguments` with schema-based validation:

```python
def _tool_schema(name: str) -> Optional[Dict[str, Any]]:
    for tool in TOOL_DEFINITIONS:
        if tool["name"] == name:
            return tool["inputSchema"]
    return None


def _value_matches_schema(value: Any, schema: Dict[str, Any]) -> bool:
    if "oneOf" in schema:
        return any(_value_matches_schema(value, option) for option in schema["oneOf"])
    schema_type = schema.get("type")
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "null":
        return value is None
    if schema_type == "array":
        if not isinstance(value, list):
            return False
        item_schema = schema.get("items")
        if item_schema is None:
            return True
        return all(_value_matches_schema(item, item_schema) for item in value)
    if schema_type == "object":
        return isinstance(value, dict)
    return True


def _validate_tool_arguments(name: str, arguments: Dict[str, Any]) -> Optional[str]:
    schema = _tool_schema(name)
    if schema is None:
        return None
    properties = schema.get("properties", {})
    extra_keys = sorted(set(arguments) - set(properties))
    if extra_keys and schema.get("additionalProperties") is False:
        return f"Invalid params: unexpected argument {extra_keys[0]}"
    for key in schema.get("required", []):
        if key not in arguments:
            return f"Invalid params: missing argument {key}"
    for key, value in arguments.items():
        prop_schema = properties.get(key)
        if prop_schema is not None and not _value_matches_schema(value, prop_schema):
            return f"Invalid params: {key} has invalid type"
    return None
```

- [ ] **Step 8: Run MCP tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_tools tests.codex_plugin.test_server -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add codex_plugin/blendex_mcp/tools.py codex_plugin/blendex_mcp/server.py tests/codex_plugin/test_tools.py tests/codex_plugin/test_server.py
git commit -m "feat: expose BlendeX v0.2 MCP tools"
```

---

### Task 3: Semantic Catalog and Socket-Aware Capabilities

**Files:**
- Modify: `codex_plugin/blendex_mcp/catalog.py`
- Modify: `blender_addon/blendex/capabilities.py`
- Modify: `tests/blender_addon/test_capabilities_fake.py`

- [ ] **Step 1: Add failing semantic and capability tests**

Append these tests to `tests/blender_addon/test_capabilities_fake.py` inside `CapabilityTests`:

```python
    def test_scan_merges_semantic_catalog_for_available_nodes_only(self):
        class Runtime:
            version = (4, 3, 0)
            node_types = {
                "GeometryNodeJoinGeometry": {"inputs": [], "outputs": [], "metadata_complete": False}
            }

        result = scan_capabilities(Runtime())

        self.assertIn("semantic", result["node_types"]["GeometryNodeJoinGeometry"])
        self.assertNotIn("GeometryNodeRealizeInstances", result["node_types"])

    def test_scan_bpy_capabilities_reads_template_sockets_when_available(self):
        class FakeSocketTemplate:
            def __init__(self, name, identifier, bl_socket_idname):
                self.name = name
                self.identifier = identifier
                self.bl_socket_idname = bl_socket_idname

        class GeometryNodeJoinGeometry:
            @classmethod
            def input_template(cls, index):
                if index == 0:
                    return FakeSocketTemplate("Geometry", "Geometry", "NodeSocketGeometry")
                raise RuntimeError("end")

            @classmethod
            def output_template(cls, index):
                if index == 0:
                    return FakeSocketTemplate("Geometry", "Geometry", "NodeSocketGeometry")
                raise RuntimeError("end")

        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return [GeometryNodeJoinGeometry]

        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(4, 3, 0)),
            types=types.SimpleNamespace(GeometryNode=GeometryNode),
        )

        previous_bpy = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            result = scan_bpy_capabilities()
        finally:
            if previous_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = previous_bpy

        node = result["node_types"]["GeometryNodeJoinGeometry"]
        self.assertTrue(node["metadata_complete"])
        self.assertEqual(node["inputs"][0]["name"], "Geometry")
        self.assertEqual(node["outputs"][0]["socket_type"], "NodeSocketGeometry")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.blender_addon.test_capabilities_fake -v
```

Expected: FAIL because semantic merge and socket templates are not implemented.

- [ ] **Step 3: Expand semantic catalog**

Replace `codex_plugin/blendex_mcp/catalog.py` with:

```python
from typing import Any, Dict


SEMANTIC_NODE_CATALOG: Dict[str, Dict[str, Any]] = {
    "NodeGroupInput": {
        "role": "Provides group input geometry and exposed parameters.",
        "common_use": "Start geometry flow from the modifier input.",
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use as the first geometry source in simple pass-through graphs."],
        "common_pairings": ["NodeGroupOutput", "GeometryNodeJoinGeometry"],
    },
    "NodeGroupOutput": {
        "role": "Receives final geometry for the modifier output.",
        "common_use": "End a Geometry Nodes graph.",
        "typical_inputs": ["Geometry"],
        "planning_hints": ["Ensure exactly one final geometry flow reaches Group Output."],
        "common_pairings": ["GeometryNodeJoinGeometry", "GeometryNodeRealizeInstances"],
    },
    "GeometryNodeJoinGeometry": {
        "role": "Combines multiple geometry streams into one output.",
        "common_use": "Merge generated pieces before sending to Group Output.",
        "typical_inputs": ["Geometry"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Place near the end of graphs that combine source and generated geometry."],
        "common_pairings": ["NodeGroupOutput", "GeometryNodeInstanceOnPoints"],
    },
    "GeometryNodeInstanceOnPoints": {
        "role": "Places instances on point geometry.",
        "common_use": "Scatter repeated modules on generated or existing points.",
        "typical_inputs": ["Points", "Instance", "Selection", "Rotation", "Scale"],
        "typical_outputs": ["Instances"],
        "planning_hints": ["Realize instances before downstream mesh-only operations."],
        "common_pairings": ["GeometryNodeDistributePointsOnFaces", "GeometryNodeRealizeInstances"],
    },
    "GeometryNodeRealizeInstances": {
        "role": "Converts instances into realized geometry.",
        "common_use": "Apply downstream mesh operations after instancing.",
        "typical_inputs": ["Geometry"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use after instance-heavy sections when later nodes need real geometry."],
        "common_pairings": ["GeometryNodeInstanceOnPoints", "GeometryNodeJoinGeometry"],
    },
    "GeometryNodeSetPosition": {
        "role": "Offsets point or mesh positions.",
        "common_use": "Warp, lift, or procedurally deform geometry.",
        "typical_inputs": ["Geometry", "Selection", "Position", "Offset"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use vector math or random values to drive the Offset input."],
        "common_pairings": ["ShaderNodeVectorMath", "FunctionNodeRandomValue"],
    },
    "GeometryNodeTransform": {
        "role": "Applies translation, rotation, and scale to geometry.",
        "common_use": "Move or resize generated geometry streams.",
        "typical_inputs": ["Geometry", "Translation", "Rotation", "Scale"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use before join nodes to arrange generated modules."],
        "common_pairings": ["GeometryNodeJoinGeometry"],
    },
    "GeometryNodeSetMaterial": {
        "role": "Assigns a material to geometry.",
        "common_use": "Apply generated or existing materials to procedural output.",
        "typical_inputs": ["Geometry", "Selection", "Material"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Place after geometry creation and before final output."],
        "common_pairings": ["NodeGroupOutput", "GeometryNodeJoinGeometry"],
    },
    "FunctionNodeRandomValue": {
        "role": "Generates deterministic random values.",
        "common_use": "Drive varied scale, rotation, color, or offsets.",
        "typical_inputs": ["Min", "Max", "ID", "Seed"],
        "typical_outputs": ["Value"],
        "planning_hints": ["Connect to transform, scale, or selection inputs for variation."],
        "common_pairings": ["GeometryNodeInstanceOnPoints", "GeometryNodeSetPosition"],
    },
    "ShaderNodeMath": {
        "role": "Computes scalar math values.",
        "common_use": "Scale, clamp, remap, or combine numeric fields.",
        "typical_inputs": ["Value"],
        "typical_outputs": ["Value"],
        "planning_hints": ["Use for simple numeric shaping before socket values or fields."],
        "common_pairings": ["FunctionNodeRandomValue"],
    },
    "ShaderNodeVectorMath": {
        "role": "Computes vector math values.",
        "common_use": "Build offsets, directions, and vector transforms.",
        "typical_inputs": ["Vector"],
        "typical_outputs": ["Vector"],
        "planning_hints": ["Use before position or transform nodes for procedural movement."],
        "common_pairings": ["GeometryNodeSetPosition"],
    },
}


def semantic_for_node(node_type: str) -> Dict[str, Any]:
    return dict(SEMANTIC_NODE_CATALOG.get(node_type, {}))
```

- [ ] **Step 4: Implement socket template scanning**

In `blender_addon/blendex/capabilities.py`, import the semantic helper and add these functions:

```python
try:
    from codex_plugin.blendex_mcp.catalog import semantic_for_node
except Exception:
    def semantic_for_node(node_type: str) -> Dict[str, Any]:
        return {}


def _socket_template_to_dict(template: Any) -> Dict[str, Any]:
    return {
        "name": getattr(template, "name", ""),
        "identifier": getattr(template, "identifier", getattr(template, "name", "")),
        "socket_type": getattr(template, "bl_socket_idname", template.__class__.__name__),
    }


def _read_templates(node_class: Any, method_name: str) -> list:
    method = getattr(node_class, method_name, None)
    if not callable(method):
        return []
    sockets = []
    index = 0
    while index < 64:
        try:
            template = method(index)
        except Exception:
            break
        if template is None:
            break
        sockets.append(_socket_template_to_dict(template))
        index += 1
    return sockets


def _node_capability(identifier: str, node_class: Any = None) -> Dict[str, Any]:
    inputs = _read_templates(node_class, "input_template") if node_class is not None else []
    outputs = _read_templates(node_class, "output_template") if node_class is not None else []
    metadata_complete = bool(inputs or outputs)
    capability = {
        "display_name": identifier,
        "inputs": inputs,
        "outputs": outputs,
        "metadata_complete": metadata_complete,
    }
    semantic = semantic_for_node(identifier)
    if semantic:
        capability["semantic"] = semantic
    return capability
```

- [ ] **Step 5: Update `scan_capabilities` and `scan_bpy_capabilities`**

Update `scan_capabilities` so it merges semantic metadata:

```python
def scan_capabilities(runtime: Any) -> Dict[str, Any]:
    version = list(getattr(runtime, "version", (0, 0, 0)))
    raw_node_types = getattr(runtime, "node_types", {})
    node_types = {}
    for node_type, metadata in raw_node_types.items():
        node_metadata = dict(metadata)
        node_metadata.setdefault("inputs", [])
        node_metadata.setdefault("outputs", [])
        node_metadata.setdefault("metadata_complete", bool(node_metadata["inputs"] or node_metadata["outputs"]))
        semantic = semantic_for_node(node_type)
        if semantic:
            node_metadata["semantic"] = semantic
        node_types[node_type] = node_metadata
    return {
        "blender_version": version,
        "node_types": node_types,
        "supported_operations": sorted(IMPLEMENTED_OPERATIONS),
    }
```

Update `scan_bpy_capabilities`:

```python
def scan_bpy_capabilities() -> Dict[str, Any]:
    import bpy

    node_types: Dict[str, Dict[str, Any]] = {}
    for subclass in bpy.types.GeometryNode.__subclasses__():
        identifier = getattr(subclass, "__name__", "")
        if identifier.startswith("GeometryNode"):
            node_types[identifier] = _node_capability(identifier, subclass)
    runtime = type("BpyRuntime", (), {"version": bpy.app.version, "node_types": node_types})()
    return scan_capabilities(runtime)
```

- [ ] **Step 6: Update implemented operations**

In `blender_addon/blendex/capabilities.py`, replace `IMPLEMENTED_OPERATIONS` with:

```python
IMPLEMENTED_OPERATIONS = {
    "capabilities.scan",
    "capabilities.supported_operations",
    "scene.inspect",
    "scene.create_carrier_mesh",
    "geometry_nodes.create_modifier",
    "geometry_nodes.inspect_tree",
    "geometry_nodes.create_node",
    "geometry_nodes.link_sockets",
    "geometry_nodes.set_socket_value",
    "geometry_nodes.label_node",
    "geometry_nodes.mark_ownership",
    "safety.validate_batch",
    "safety.dry_run",
}
```

- [ ] **Step 7: Run capability tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_capabilities_fake -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add codex_plugin/blendex_mcp/catalog.py blender_addon/blendex/capabilities.py tests/blender_addon/test_capabilities_fake.py
git commit -m "feat: add socket-aware BlendeX capabilities"
```

---

### Task 4: Scene Operations and Rich Scene Inspection

**Files:**
- Create: `blender_addon/blendex/scene.py`
- Modify: `blender_addon/blendex/server.py`
- Create: `tests/blender_addon/test_scene.py`
- Modify: `tests/blender_addon/test_server_dispatch.py`

- [ ] **Step 1: Add fake scene tests**

Create `tests/blender_addon/test_scene.py`:

```python
import unittest

from blender_addon.blendex.scene import create_carrier_mesh, inspect_scene


class FakeModifier:
    def __init__(self, name, modifier_type="NODES", owned=False, node_group=None):
        self.name = name
        self.type = modifier_type
        self.node_group = node_group
        self.props = {"blendex_owned": owned}

    def get(self, key, default=None):
        return self.props.get(key, default)


class FakeObject:
    def __init__(self, name, object_type="MESH"):
        self.name = name
        self.type = object_type
        self.modifiers = []
        self.hide_viewport = False
        self.selected = False

    def select_get(self):
        return self.selected


class FakeObjectStore(list):
    def get(self, name):
        for obj in self:
            if obj.name == name:
                return obj
        return None


class FakeContext:
    def __init__(self):
        self.objects = FakeObjectStore()
        cube = FakeObject("Cube")
        cube.selected = True
        cube.modifiers.append(FakeModifier("BlendeX Geometry", owned=True, node_group=type("Group", (), {"name": "BlendeX Geometry Nodes"})()))
        plane = FakeObject("Plane")
        self.objects.extend([cube, plane])
        self.selected_objects = [cube]
        self.object = cube
        self.created = []

    def create_mesh_object(self, name):
        obj = FakeObject(name)
        obj.selected = True
        self.objects.append(obj)
        self.object = obj
        self.selected_objects = [obj]
        self.created.append(obj)
        return obj


class SceneTests(unittest.TestCase):
    def test_inspect_scene_returns_selection_modifiers_and_recommended_target(self):
        context = FakeContext()

        result = inspect_scene(context)

        self.assertEqual(result["selected_object"], "Cube")
        self.assertEqual(result["recommended_target"]["object_id"], "Cube")
        self.assertTrue(result["objects"][0]["modifiers"][0]["blendex_owned"])
        self.assertTrue(result["objects"][0]["modifiers"][0]["safe_for_mutation"])

    def test_create_carrier_mesh_uses_context_factory(self):
        context = FakeContext()

        result = create_carrier_mesh(context, "Generated Carrier")

        self.assertEqual(result["object_id"], "Generated Carrier")
        self.assertEqual(context.object.name, "Generated Carrier")
        self.assertEqual(result["selected_object"], "Generated Carrier")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.blender_addon.test_scene -v
```

Expected: FAIL with `ModuleNotFoundError` for `blender_addon.blendex.scene`.

- [ ] **Step 3: Create scene helper module**

Create `blender_addon/blendex/scene.py`:

```python
from typing import Any, Dict, List, Optional


def _modifier_summary(modifier: Any) -> Dict[str, Any]:
    getter = getattr(modifier, "get", None)
    owned = bool(getter("blendex_owned", False)) if callable(getter) else False
    node_group = getattr(modifier, "node_group", None)
    modifier_type = getattr(modifier, "type", "")
    return {
        "name": getattr(modifier, "name", ""),
        "type": modifier_type,
        "blendex_owned": owned,
        "safe_for_mutation": modifier_type == "NODES" and owned,
        "node_group": getattr(node_group, "name", None),
    }


def _is_selected(obj: Any, selected_names: set) -> bool:
    select_get = getattr(obj, "select_get", None)
    if callable(select_get):
        return bool(select_get())
    return getattr(obj, "name", "") in selected_names


def _object_summary(obj: Any, selected_names: set) -> Dict[str, Any]:
    modifiers = [_modifier_summary(modifier) for modifier in getattr(obj, "modifiers", [])]
    return {
        "id": getattr(obj, "name", ""),
        "name": getattr(obj, "name", ""),
        "type": getattr(obj, "type", ""),
        "selected": _is_selected(obj, selected_names),
        "visible": not bool(getattr(obj, "hide_viewport", False)),
        "modifiers": modifiers,
    }


def _recommended_target(objects: List[Dict[str, Any]], selected_object: Optional[str]) -> Optional[Dict[str, Any]]:
    if selected_object:
        for obj in objects:
            if obj["id"] != selected_object:
                continue
            for modifier in obj["modifiers"]:
                if modifier["safe_for_mutation"]:
                    return {"object_id": obj["id"], "modifier_id": modifier["name"], "reason": "selected_blendex_modifier"}
            if obj["type"] == "MESH":
                return {"object_id": obj["id"], "reason": "selected_mesh_without_blendex_modifier"}
    return None


def inspect_scene(context: Any) -> Dict[str, Any]:
    selected_objects = list(getattr(context, "selected_objects", []))
    selected_names = {getattr(obj, "name", "") for obj in selected_objects}
    active_object = getattr(context, "object", None)
    object_store = getattr(context, "objects", [])
    objects = [_object_summary(obj, selected_names) for obj in object_store]
    selected_object = getattr(active_object, "name", None) if active_object is not None else None
    return {
        "objects": objects,
        "selected_objects": sorted(name for name in selected_names if name),
        "selected_object": selected_object,
        "recommended_target": _recommended_target(objects, selected_object),
    }


def create_carrier_mesh(context: Any, name: str = "BlendeX Carrier") -> Dict[str, Any]:
    factory = getattr(context, "create_mesh_object", None)
    if callable(factory):
        obj = factory(name)
    else:
        import bpy

        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
        obj.name = name
    return {"object_id": obj.name, "name": obj.name, "selected_object": obj.name}


def bpy_scene_context() -> Any:
    import bpy

    class BpySceneContext:
        objects = bpy.data.objects
        selected_objects = getattr(bpy.context, "selected_objects", [])
        object = getattr(bpy.context, "object", None)

    return BpySceneContext()
```

- [ ] **Step 4: Update server dispatch for scene helpers**

In `blender_addon/blendex/server.py`, replace `_inspect_bpy_scene` with:

```python
def _inspect_bpy_scene() -> Dict[str, Any]:
    from .scene import bpy_scene_context, inspect_scene

    return inspect_scene(bpy_scene_context())


def _create_bpy_carrier_mesh(name: str) -> Dict[str, Any]:
    from .scene import bpy_scene_context, create_carrier_mesh

    return create_carrier_mesh(bpy_scene_context(), name)
```

In `dispatch_payload`, add this branch after `scene.inspect`:

```python
        elif request.type == "scene.create_carrier_mesh":
            result = _create_bpy_carrier_mesh(request.params.get("name", "BlendeX Carrier"))
```

In `_dispatch_payload_with_factory`, include `scene.create_carrier_mesh` in the set that stays on main thread but does not require the Geometry Nodes executor factory:

```python
        "scene.create_carrier_mesh",
```

- [ ] **Step 5: Add dispatch test for carrier mesh**

Append this test to `DispatchTests` in `tests/blender_addon/test_server_dispatch.py`:

```python
    def test_dispatch_handles_carrier_mesh_creation_without_executor(self):
        original = server._create_bpy_carrier_mesh
        server._create_bpy_carrier_mesh = lambda name: {"object_id": name, "selected_object": name}
        try:
            response = dispatch_payload(
                {
                    "id": "req_carrier",
                    "type": "scene.create_carrier_mesh",
                    "target": {},
                    "params": {"name": "BlendeX Carrier"},
                },
                executor=None,
            )
        finally:
            server._create_bpy_carrier_mesh = original

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["object_id"], "BlendeX Carrier")
```

- [ ] **Step 6: Run scene and dispatch tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_scene tests.blender_addon.test_server_dispatch -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add blender_addon/blendex/scene.py blender_addon/blendex/server.py tests/blender_addon/test_scene.py tests/blender_addon/test_server_dispatch.py
git commit -m "feat: add BlendeX scene graph context"
```

---

### Task 5: Geometry Nodes Executor Graph Mutations

**Files:**
- Modify: `blender_addon/blendex/executor.py`
- Modify: `tests/blender_addon/test_executor_fake.py`

- [ ] **Step 1: Expand fake Blender graph types**

In `tests/blender_addon/test_executor_fake.py`, replace the fake classes above `ExecutorTests` with versions that support sockets, modifier creation, and links:

```python
class FakeSocket:
    def __init__(self, name, socket_type="NodeSocketGeometry", is_output=False, default_value=None):
        self.name = name
        self.identifier = name
        self.bl_socket_idname = socket_type
        self.is_output = is_output
        self.default_value = default_value


class FakeSocketList(list):
    def get(self, name):
        for socket in self:
            if socket.name == name or socket.identifier == name:
                return socket
        return None


class FakeBlenderNode:
    def __init__(self, name, bl_idname):
        self.name = name
        self.bl_idname = bl_idname
        self.label = ""
        self.location = [0, 0]
        self.inputs = FakeSocketList([FakeSocket("Value", "NodeSocketFloat", default_value=0.0)])
        self.outputs = FakeSocketList([FakeSocket("Geometry", "NodeSocketGeometry", is_output=True)])


class FakeBlenderLink:
    def __init__(self, from_node, from_socket, to_node, to_socket):
        self.from_node = from_node
        self.from_socket = from_socket
        self.to_node = to_node
        self.to_socket = to_socket


class FakeLinkCollection(list):
    def new(self, from_socket, to_socket):
        link = FakeBlenderLink(from_socket.owner, from_socket, to_socket.owner, to_socket)
        self.append(link)
        return link


class FakeBlenderNodeCollection:
    def __init__(self):
        self.created = []

    def new(self, type):
        node = FakeBlenderNode(f"{type}.{len(self.created) + 1:03d}", type)
        for socket in node.inputs + node.outputs:
            socket.owner = node
        self.created.append(node)
        return node

    def get(self, name):
        for node in self.created:
            if node.name == name:
                return node
        return None

    def __iter__(self):
        return iter(self.created)


class FakeNodeTree:
    def __init__(self):
        self.name = "BlendeX Geometry Nodes"
        self.nodes = {}
        self.links = []
        self.props = {}

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)


class FakeModifier:
    def __init__(self, name, owned=True):
        self.name = name
        self.type = "NODES"
        self.node_group = FakeNodeTree()
        self.props = {}
        if owned:
            self["blendex_owned"] = True
            self.node_group["blendex_owned"] = True

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)


class FakeModifierCollection(dict):
    def new(self, name, type):
        modifier = FakeModifier(name)
        modifier.type = type
        self[name] = modifier
        return modifier


class FakeObject:
    def __init__(self, name):
        self.name = name
        self.modifiers = FakeModifierCollection({"BlendeX Geometry": FakeModifier("BlendeX Geometry")})


class FakeContext:
    def __init__(self):
        self.objects = {"Cube": FakeObject("Cube")}
        self.node_types = {
            "GeometryNodeJoinGeometry": {"inputs": [{"name": "Geometry", "socket_type": "NodeSocketGeometry"}], "outputs": [{"name": "Geometry", "socket_type": "NodeSocketGeometry"}]},
            "ShaderNodeValue": {"inputs": [{"name": "Value", "socket_type": "NodeSocketFloat"}], "outputs": [{"name": "Value", "socket_type": "NodeSocketFloat"}]},
        }
```

- [ ] **Step 2: Add failing executor tests**

Append these tests to `ExecutorTests`:

```python
    def test_create_modifier_marks_modifier_and_node_group_owned(self):
        context = FakeContext()
        context.objects["Cube"].modifiers.pop("BlendeX Geometry")
        executor = GeometryNodesExecutor(context)

        result = executor.execute(
            OperationRequest(
                id="req_modifier",
                type="geometry_nodes.create_modifier",
                target={"object_id": "Cube"},
                params={"modifier_id": "BlendeX Geometry"},
            )
        )

        modifier = context.objects["Cube"].modifiers["BlendeX Geometry"]
        self.assertEqual(result["modifier_id"], "BlendeX Geometry")
        self.assertTrue(modifier.get("blendex_owned"))
        self.assertTrue(modifier.node_group.get("blendex_owned"))

    def test_set_socket_value_updates_input_default(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        node = tree.nodes.new(type="ShaderNodeValue")
        executor = GeometryNodesExecutor(context)

        result = executor.execute(
            OperationRequest(
                id="req_value",
                type="geometry_nodes.set_socket_value",
                target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                params={"node_id": node.name, "socket": "Value", "value": 4.25},
            )
        )

        self.assertEqual(result["value"], 4.25)
        self.assertEqual(node.inputs.get("Value").default_value, 4.25)

    def test_link_sockets_creates_link_between_compatible_sockets(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = FakeLinkCollection()
        from_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node.inputs = FakeSocketList([FakeSocket("Geometry", "NodeSocketGeometry")])
        for socket in to_node.inputs:
            socket.owner = to_node
        executor = GeometryNodesExecutor(context)

        result = executor.execute(
            OperationRequest(
                id="req_link",
                type="geometry_nodes.link_sockets",
                target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                params={
                    "from_node": from_node.name,
                    "from_socket": "Geometry",
                    "to_node": to_node.name,
                    "to_socket": "Geometry",
                },
            )
        )

        self.assertEqual(result["from_node"], from_node.name)
        self.assertEqual(len(tree.links), 1)

    def test_label_node_updates_label(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)

        result = executor.execute(
            OperationRequest(
                id="req_label",
                type="geometry_nodes.label_node",
                target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                params={"node_id": node.name, "label": "Readable Join"},
            )
        )

        self.assertEqual(result["label"], "Readable Join")
        self.assertEqual(node.label, "Readable Join")
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.blender_addon.test_executor_fake -v
```

Expected: FAIL because executor does not implement v0.2 graph mutations.

- [ ] **Step 4: Add executor routing**

In `GeometryNodesExecutor.execute`, add branches before the unsupported-operation error:

```python
        if request.type == "geometry_nodes.create_modifier":
            return self._create_modifier(request)
        if request.type == "geometry_nodes.link_sockets":
            return self._link_sockets(request)
        if request.type == "geometry_nodes.set_socket_value":
            return self._set_socket_value(request)
        if request.type == "geometry_nodes.label_node":
            return self._label_node(request)
        if request.type == "geometry_nodes.mark_ownership":
            return self._mark_ownership(request)
```

- [ ] **Step 5: Add generic collection helpers**

Add these methods to `GeometryNodesExecutor` after `_is_blendex_owned`:

```python
    def _set_blendex_owned(self, item: Any) -> None:
        try:
            item["blendex_owned"] = True
        except Exception:
            setattr(item, "blendex_owned", True)

    def _collection_get(self, collection: Any, key: str) -> Any:
        getter = getattr(collection, "get", None)
        if callable(getter):
            return getter(key)
        if isinstance(collection, dict):
            return collection.get(key)
        for item in collection:
            if getattr(item, "name", None) == key:
                return item
        return None

    def _node(self, tree: Any, node_id: str) -> Any:
        node = self._collection_get(tree.nodes, node_id)
        if node is None:
            raise BlendexError("NODE_TYPE_NOT_FOUND", f"Node not found: {node_id}")
        return node

    def _socket(self, node: Any, socket_name: str, direction: str) -> Any:
        sockets = getattr(node, "outputs" if direction == "output" else "inputs", [])
        socket = self._collection_get(sockets, socket_name)
        if socket is None:
            raise BlendexError("SOCKET_NOT_FOUND", f"Socket not found: {socket_name}")
        return socket

    def _socket_type(self, socket: Any) -> str:
        return getattr(socket, "bl_socket_idname", socket.__class__.__name__)
```

- [ ] **Step 6: Implement modifier creation and ownership**

Add these methods to `GeometryNodesExecutor`:

```python
    def _create_modifier(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier_id = request.params.get("modifier_id", "BlendeX Geometry")
        existing = self._collection_get(obj.modifiers, modifier_id)
        if existing is not None:
            if getattr(existing, "type", "") != "NODES":
                raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier is not a Geometry Nodes modifier: {modifier_id}")
            modifier = existing
        else:
            creator = getattr(obj.modifiers, "new", None)
            if not callable(creator):
                raise BlendexError("MODIFIER_NOT_FOUND", f"Object cannot create modifiers: {request.target['object_id']}")
            modifier = creator(name=modifier_id, type="NODES")
        self._set_blendex_owned(modifier)
        tree = self._node_tree(modifier)
        self._set_blendex_owned(tree)
        return {
            "object_id": obj.name,
            "modifier_id": modifier.name,
            "node_group_id": getattr(tree, "name", modifier.name),
            "blendex_owned": True,
        }

    def _mark_ownership(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        self._set_blendex_owned(modifier)
        tree = self._node_tree(modifier)
        self._set_blendex_owned(tree)
        return {"object_id": obj.name, "modifier_id": modifier.name, "blendex_owned": True}
```

- [ ] **Step 7: Return socket summaries from node creation and inspection**

Add:

```python
    def _inspect_socket(self, socket: Any, direction: str) -> Dict[str, Any]:
        result = {
            "name": getattr(socket, "name", ""),
            "identifier": getattr(socket, "identifier", getattr(socket, "name", "")),
            "direction": direction,
            "socket_type": self._socket_type(socket),
        }
        if hasattr(socket, "default_value"):
            result["value"] = getattr(socket, "default_value")
        return result

    def _inspect_node(self, node: Any) -> Dict[str, Any]:
        if isinstance(node, dict):
            return node
        return {
            "id": getattr(node, "name", ""),
            "node_type": getattr(node, "bl_idname", ""),
            "label": getattr(node, "label", ""),
            "location": list(getattr(node, "location", [0, 0])),
            "inputs": [self._inspect_socket(socket, "input") for socket in getattr(node, "inputs", [])],
            "outputs": [self._inspect_socket(socket, "output") for socket in getattr(node, "outputs", [])],
        }
```

Update `_create_node` real-Blender return:

```python
            return self._inspect_node(node)
```

Update `_inspect_tree` non-dict node path:

```python
            nodes = [self._inspect_node(node) for node in tree.nodes]
```

- [ ] **Step 8: Implement socket value, link, and label operations**

Add:

```python
    def _set_socket_value(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"), require_ownership=True)
        tree = self._node_tree(modifier)
        node = self._node(tree, request.params["node_id"])
        socket = self._socket(node, request.params["socket"], "input")
        value = request.params["value"]
        current = getattr(socket, "default_value", None)
        if current is not None and not isinstance(value, type(current)):
            if not (isinstance(current, float) and isinstance(value, (int, float))):
                raise BlendexError("VALUE_TYPE_MISMATCH", f"Socket value type mismatch for {request.params['socket']}.")
        try:
            socket.default_value = value
        except Exception as exc:
            raise BlendexError("VALUE_TYPE_MISMATCH", f"Could not set socket value for {request.params['socket']}.", details={"exception": str(exc)})
        return {"node_id": getattr(node, "name", request.params["node_id"]), "socket": request.params["socket"], "value": value}

    def _link_sockets(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"), require_ownership=True)
        tree = self._node_tree(modifier)
        from_node = self._node(tree, request.params["from_node"])
        to_node = self._node(tree, request.params["to_node"])
        from_socket = self._socket(from_node, request.params["from_socket"], "output")
        to_socket = self._socket(to_node, request.params["to_socket"], "input")
        if self._socket_type(from_socket) != self._socket_type(to_socket):
            raise BlendexError("SOCKET_TYPE_MISMATCH", "Cannot link sockets with different socket types.")
        creator = getattr(tree.links, "new", None)
        if callable(creator):
            creator(from_socket, to_socket)
        else:
            tree.links.append({
                "from_node": getattr(from_node, "name", request.params["from_node"]),
                "from_socket": request.params["from_socket"],
                "to_node": getattr(to_node, "name", request.params["to_node"]),
                "to_socket": request.params["to_socket"],
            })
        return {
            "from_node": getattr(from_node, "name", request.params["from_node"]),
            "from_socket": request.params["from_socket"],
            "to_node": getattr(to_node, "name", request.params["to_node"]),
            "to_socket": request.params["to_socket"],
        }

    def _label_node(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"), require_ownership=True)
        tree = self._node_tree(modifier)
        node = self._node(tree, request.params["node_id"])
        node.label = request.params["label"]
        return {"node_id": getattr(node, "name", request.params["node_id"]), "label": node.label}
```

- [ ] **Step 9: Run executor tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_executor_fake -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add blender_addon/blendex/executor.py tests/blender_addon/test_executor_fake.py
git commit -m "feat: implement BlendeX graph mutations"
```

---

### Task 6: Batch Validation and Dry Run

**Files:**
- Create: `blender_addon/blendex/safety.py`
- Modify: `blender_addon/blendex/server.py`
- Create: `tests/blender_addon/test_safety.py`
- Modify: `tests/blender_addon/test_server_dispatch.py`

- [ ] **Step 1: Add failing safety tests**

Create `tests/blender_addon/test_safety.py`:

```python
import unittest

from blender_addon.blendex.safety import dry_run_operations, validate_operations


class RecordingExecutor:
    def __init__(self, failing_type=None):
        self.failing_type = failing_type

    def validate(self, request):
        if request.type == self.failing_type:
            from blendex_protocol.errors import BlendexError

            raise BlendexError("SOCKET_NOT_FOUND", "Socket missing.", retry_hint="Inspect the tree first.")
        return {"validated": True}


class SafetyTests(unittest.TestCase):
    def test_validate_operations_returns_valid_status(self):
        result = validate_operations(
            [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}],
            RecordingExecutor(),
        )

        self.assertEqual(result["status"], "valid")
        self.assertTrue(result["operations"][0]["ok"])

    def test_validate_operations_returns_invalid_entry(self):
        result = validate_operations(
            [
                {
                    "id": "op_bad",
                    "type": "geometry_nodes.set_socket_value",
                    "target": {"object_id": "Cube"},
                    "params": {"node_id": "Value", "socket": "Missing", "value": 1.0},
                }
            ],
            RecordingExecutor(failing_type="geometry_nodes.set_socket_value"),
        )

        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["operations"][0]["ok"])
        self.assertEqual(result["operations"][0]["error"]["code"], "SOCKET_NOT_FOUND")

    def test_dry_run_returns_preview_sections(self):
        result = dry_run_operations(
            [
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "client_id": "join_1"},
                },
                {
                    "id": "op_link",
                    "type": "geometry_nodes.link_sockets",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {
                        "from_node": "Group Input",
                        "from_socket": "Geometry",
                        "to_node": "join_1",
                        "to_socket": "Geometry",
                    },
                },
            ],
            RecordingExecutor(),
        )

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["preview"]["nodes"][0]["client_id"], "join_1")
        self.assertEqual(result["preview"]["links"][0]["to_node"], "join_1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.blender_addon.test_safety -v
```

Expected: FAIL with `ModuleNotFoundError` for `blender_addon.blendex.safety`.

- [ ] **Step 3: Add executor validation method**

In `GeometryNodesExecutor`, add this method:

```python
    def validate(self, request: OperationRequest) -> Dict[str, Any]:
        validate_request(request)
        if request.type == "geometry_nodes.create_node":
            node_type = request.params["node_type"]
            if node_type not in self.context.node_types:
                raise BlendexError("NODE_TYPE_NOT_FOUND", f"Node type is unavailable: {node_type}")
            obj = self._object(request.target["object_id"])
            self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"), require_ownership=True)
        elif request.type in {
            "geometry_nodes.inspect_tree",
            "geometry_nodes.link_sockets",
            "geometry_nodes.set_socket_value",
            "geometry_nodes.label_node",
            "geometry_nodes.mark_ownership",
        }:
            obj = self._object(request.target["object_id"])
            self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"), require_ownership=request.type != "geometry_nodes.inspect_tree")
        elif request.type == "geometry_nodes.create_modifier":
            self._object(request.target["object_id"])
        return {"validated": True}
```

- [ ] **Step 4: Create safety module**

Create `blender_addon/blendex/safety.py`:

```python
from typing import Any, Dict, List

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


def _validate_one(operation: Dict[str, Any], index: int, executor: Any) -> Dict[str, Any]:
    try:
        request = OperationRequest.from_dict(operation)
        validate_request(request)
        validator = getattr(executor, "validate", None)
        if callable(validator) and request.type.startswith("geometry_nodes."):
            validator(request)
        return {"index": index, "id": request.id, "type": request.type, "ok": True, "message": "OK"}
    except BlendexError as error:
        return {
            "index": index,
            "id": str(operation.get("id", f"op_{index}")) if isinstance(operation, dict) else f"op_{index}",
            "type": str(operation.get("type", "")) if isinstance(operation, dict) else "",
            "ok": False,
            "error": error.to_dict(),
        }


def validate_operations(operations: List[Dict[str, Any]], executor: Any) -> Dict[str, Any]:
    results = [_validate_one(operation, index, executor) for index, operation in enumerate(operations)]
    failed = [entry for entry in results if not entry["ok"]]
    status = "valid" if not failed else "invalid"
    return {"status": status, "operations": results}


def _preview_for(operation: Dict[str, Any]) -> Dict[str, Any]:
    operation_type = operation.get("type")
    target = operation.get("target", {})
    params = operation.get("params", {})
    if operation_type == "scene.create_carrier_mesh":
        return {"section": "objects", "name": params.get("name", "BlendeX Carrier")}
    if operation_type == "geometry_nodes.create_modifier":
        return {"section": "modifiers", "object_id": target.get("object_id"), "modifier_id": params.get("modifier_id", "BlendeX Geometry")}
    if operation_type == "geometry_nodes.create_node":
        return {
            "section": "nodes",
            "object_id": target.get("object_id"),
            "modifier_id": target.get("modifier_id", "BlendeX Geometry"),
            "node_type": params.get("node_type"),
            "client_id": params.get("client_id"),
            "label": params.get("label", params.get("node_type")),
        }
    if operation_type == "geometry_nodes.set_socket_value":
        return {"section": "socket_values", "node_id": params.get("node_id"), "socket": params.get("socket"), "value": params.get("value")}
    if operation_type == "geometry_nodes.link_sockets":
        return {
            "section": "links",
            "from_node": params.get("from_node"),
            "from_socket": params.get("from_socket"),
            "to_node": params.get("to_node"),
            "to_socket": params.get("to_socket"),
        }
    return {"section": "warnings", "message": f"No preview section for {operation_type}"}


def dry_run_operations(operations: List[Dict[str, Any]], executor: Any) -> Dict[str, Any]:
    validation = validate_operations(operations, executor)
    preview = {"objects": [], "modifiers": [], "nodes": [], "socket_values": [], "links": [], "warnings": []}
    for operation in operations:
        item = _preview_for(operation)
        section = item.pop("section")
        preview[section].append(item)
    validation["preview"] = preview
    return validation
```

- [ ] **Step 5: Route safety operations in server**

In `blender_addon/blendex/server.py`, add:

```python
def _validate_batch(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    from .safety import validate_operations

    return validate_operations(request.params["operations"], executor)


def _dry_run(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    from .safety import dry_run_operations

    return dry_run_operations(request.params["operations"], executor)
```

In `dispatch_payload`, add before the final executor branch:

```python
        elif request.type == "safety.validate_batch":
            result = _validate_batch(request, executor)
        elif request.type == "safety.dry_run":
            result = _dry_run(request, executor)
```

In `_dispatch_payload_with_factory`, do not include safety operations in the no-executor set. They need the executor for graph target checks.

- [ ] **Step 6: Add server dispatch safety test**

Append this test to `DispatchTests` in `tests/blender_addon/test_server_dispatch.py`:

```python
    def test_dispatch_handles_safety_validate_batch(self):
        class ValidatingExecutor:
            def validate(self, request):
                return {"validated": True}

        response = dispatch_payload(
            {
                "id": "req_batch",
                "type": "safety.validate_batch",
                "target": {},
                "params": {
                    "operations": [
                        {"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}
                    ]
                },
            },
            executor=ValidatingExecutor(),
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "valid")
```

- [ ] **Step 7: Run safety and dispatch tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_safety tests.blender_addon.test_server_dispatch -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add blender_addon/blendex/safety.py blender_addon/blendex/server.py blender_addon/blendex/executor.py tests/blender_addon/test_safety.py tests/blender_addon/test_server_dispatch.py
git commit -m "feat: add BlendeX batch validation previews"
```

---

### Task 7: Integration Smoke and README

**Files:**
- Modify: `tests/integration/blender_smoke.py`
- Modify: `README.md`

- [ ] **Step 1: Expand Blender smoke script**

Replace the body of `main()` in `tests/integration/blender_smoke.py` with:

```python
def main():
    blendex.register()
    try:
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object

        class SmokeContext:
            def __init__(self, obj):
                self.objects = {obj.name: obj}
                self.node_types = {
                    "GeometryNodeJoinGeometry": {
                        "inputs": [{"name": "Geometry", "socket_type": "NodeSocketGeometry"}],
                        "outputs": [{"name": "Geometry", "socket_type": "NodeSocketGeometry"}],
                    }
                }

        executor = GeometryNodesExecutor(SmokeContext(obj))
        modifier = executor.execute(
            OperationRequest(
                id="smoke_modifier",
                type="geometry_nodes.create_modifier",
                target={"object_id": obj.name},
                params={"modifier_id": "BlendeX Geometry"},
            )
        )
        assert modifier["blendex_owned"] is True

        node_a = executor.execute(
            OperationRequest(
                id="smoke_node_a",
                type="geometry_nodes.create_node",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={"node_type": "GeometryNodeJoinGeometry", "label": "Join A"},
            )
        )
        node_b = executor.execute(
            OperationRequest(
                id="smoke_node_b",
                type="geometry_nodes.create_node",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={"node_type": "GeometryNodeJoinGeometry", "label": "Join B"},
            )
        )
        assert node_a["node_type"] == "GeometryNodeJoinGeometry"
        assert node_b["node_type"] == "GeometryNodeJoinGeometry"

        tree = executor.execute(
            OperationRequest(
                id="smoke_tree",
                type="geometry_nodes.inspect_tree",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={},
            )
        )
        assert len(tree["nodes"]) >= 2
    finally:
        blendex.unregister()
```

- [ ] **Step 2: Run pure tests and smoke launcher**

Run:

```bash
./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
```

Expected: unit tests PASS; smoke launcher PASS if `BLENDER` is set, otherwise prints `SKIP: set BLENDER=/path/to/blender to run the Blender smoke test`.

- [ ] **Step 3: Update README current tools**

In `README.md`, replace the "当前 MCP 工具" section with a v0.2-aware list:

```markdown
## 当前 MCP 工具

v0.2 目标工具面包括：

- `blendex_scan_capabilities`
  - 扫描连接中的 Blender runtime。
  - 返回 Blender 版本、Geometry Nodes 节点类型、socket metadata、语义 catalog 匹配和真实支持的 BlendeX 操作。

- `blendex_inspect_scene`
  - 检查当前 Blender 场景、选中对象、modifier、Geometry Nodes node group 和 BlendeX ownership。

- `blendex_create_carrier_mesh`
  - 创建一个用于承载程序化 Geometry Nodes 图的基础 mesh object。

- `blendex_create_modifier`
  - 在目标对象上创建 BlendeX-owned Geometry Nodes modifier。

- `blendex_inspect_tree`
  - 检查目标 Geometry Nodes tree 的 nodes、sockets、links、labels 和 ownership metadata。

- `blendex_create_node`
  - 在 BlendeX-owned Geometry Nodes modifier 中创建节点。

- `blendex_set_socket_value`
  - 设置节点 input socket 默认值，并在写入前做 socket 与 value 类型校验。

- `blendex_link_sockets`
  - 连接 output socket 到 input socket，并在写入前做方向和基础类型校验。

- `blendex_label_node`
  - 设置节点 label，帮助 CodeX 创建可读图结构。

- `blendex_validate_batch`
  - 验证一组结构化操作，不修改 Blender 场景。

- `blendex_dry_run`
  - 返回一组结构化操作的预览，包括将创建的节点、链接和 socket value 变化。
```

- [ ] **Step 4: Update README verification notes**

In `README.md`, extend "运行 Blender smoke test" with:

```markdown
v0.2 smoke test 会覆盖：

- 创建 BlendeX-owned Geometry Nodes modifier。
- 创建至少两个 Geometry Nodes 节点。
- inspect tree 返回创建后的节点结构。
```

- [ ] **Step 5: Run README grep check**

Run:

```bash
rg -n "blendex_link_sockets|blendex_set_socket_value|blendex_dry_run|arbitrary Python" README.md
```

Expected: output includes all four patterns.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/blender_smoke.py README.md
git commit -m "docs: document BlendeX v0.2 graph kernel"
```

---

### Task 8: Full Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Run full pure Python test suite**

Run:

```bash
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 2: Run Blender smoke launcher**

Run:

```bash
python3 scripts/run_blender_smoke.py
```

Expected: PASS if `BLENDER` is set; otherwise clean SKIP with exit code 0.

- [ ] **Step 3: Confirm no arbitrary execution path was added**

Run:

```bash
rg -n "exec\\(|eval\\(|subprocess|python\\.exec" blender_addon codex_plugin src tests
```

Expected: no arbitrary Python execution path in `blender_addon`, `codex_plugin`, or `src`. Test references to blocked `python.exec` are acceptable.

- [ ] **Step 4: Confirm supported operations and tool names align**

Run:

```bash
python3 - <<'PY'
from blender_addon.blendex.capabilities import IMPLEMENTED_OPERATIONS
from codex_plugin.blendex_mcp.tools import tool_names

print("operations")
for name in sorted(IMPLEMENTED_OPERATIONS):
    print(name)
print("tools")
for name in sorted(tool_names()):
    print(name)
PY
```

Expected output includes:

```text
geometry_nodes.create_modifier
geometry_nodes.create_node
geometry_nodes.inspect_tree
geometry_nodes.label_node
geometry_nodes.link_sockets
geometry_nodes.mark_ownership
geometry_nodes.set_socket_value
safety.dry_run
safety.validate_batch
blendex_create_modifier
blendex_create_node
blendex_inspect_tree
blendex_label_node
blendex_link_sockets
blendex_set_socket_value
blendex_dry_run
blendex_validate_batch
```

- [ ] **Step 5: Check git status**

Run:

```bash
git status --short
```

Expected: clean working tree.

- [ ] **Step 6: Do not create an empty verification commit**

If Step 1-5 required fixes, return to the task that owns the failed files, apply the fix there, and use that task's commit command. If Step 1-5 passed without edits, leave the working tree clean and do not create a Task 8 commit.

---

## Self-Review Notes

Spec coverage:

- MCP tool surface is covered by Task 2.
- Socket-aware capabilities and semantic catalog merge are covered by Task 3.
- Scene context and carrier mesh creation are covered by Task 4.
- Modifier setup, socket values, links, labels, ownership, and tree inspection are covered by Task 5.
- Batch validation and dry-run preview are covered by Task 6.
- Blender smoke and README updates are covered by Task 7.
- Final safety and regression verification is covered by Task 8.

No task implements arbitrary Python execution. No task mutates non-BlendeX-owned Geometry Nodes graphs except for read-only inspection and explicit ownership marking.
