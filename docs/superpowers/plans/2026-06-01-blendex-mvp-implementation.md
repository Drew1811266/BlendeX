# BlendeX MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working BlendeX MVP that lets a CodeX-side plugin connect to a local Blender add-on over WebSocket and apply structured Geometry Nodes operations without arbitrary Python execution.

**Architecture:** The MVP is a vertical slice through the Split Bridge architecture. A shared Python protocol package defines messages and errors, the Blender add-on runs the guarded execution server, and the CodeX plugin exposes MCP tools that forward typed requests to Blender.

**Tech Stack:** Python 3.9+, Blender `bpy`, Python stdlib `unittest`, Python stdlib `socket`/`threading` for the local WebSocket server and client, Codex plugin manifest with a stdio MCP server.

---

## Scope

This plan implements the MVP foundation from `docs/superpowers/specs/2026-06-01-blendex-design.md`. It intentionally builds one integrated vertical slice rather than separate isolated products:

- Shared protocol and validation.
- Blender add-on skeleton, UI, state, logs, capability scanner, executor, and local WebSocket service.
- CodeX plugin skeleton with MCP tool server and WebSocket client.
- Unit tests for pure Python code.
- Blender background smoke test harness that runs when a Blender executable is available.

## File Structure

- `pyproject.toml`: project metadata and unittest-friendly package layout.
- `README.md`: local development, install, and manual acceptance instructions.
- `src/blendex_protocol/__init__.py`: public protocol exports.
- `src/blendex_protocol/errors.py`: stable error codes and `BlendexError`.
- `src/blendex_protocol/messages.py`: request/response/event dataclasses and parsing helpers.
- `src/blendex_protocol/validation.py`: allowlisted operation names and payload validation.
- `tests/protocol/test_messages.py`: protocol round-trip and validation tests.
- `tests/protocol/test_validation.py`: allowlist and error behavior tests.
- `blender_addon/blendex/__init__.py`: Blender add-on metadata and registration.
- `blender_addon/blendex/state.py`: in-memory add-on state shared by UI and server.
- `blender_addon/blendex/logs.py`: operation log model.
- `blender_addon/blendex/ui.py`: Blender sidebar control and debug panel.
- `blender_addon/blendex/capabilities.py`: Blender runtime capability scanner.
- `blender_addon/blendex/executor.py`: safe Geometry Nodes operation executor.
- `blender_addon/blendex/server.py`: local WebSocket service and operation dispatch.
- `tests/blender_addon/test_state.py`: pure Python add-on state tests.
- `tests/blender_addon/test_executor_fake.py`: executor tests with fake Blender objects.
- `.codex-plugin/plugin.json`: installable CodeX plugin manifest.
- `.mcp.json`: MCP server configuration for the CodeX plugin.
- `codex_plugin/blendex_mcp/__init__.py`: MCP package marker.
- `codex_plugin/blendex_mcp/blender_client.py`: WebSocket client used by MCP tools.
- `codex_plugin/blendex_mcp/catalog.py`: semantic node catalog seed.
- `codex_plugin/blendex_mcp/tools.py`: MCP tool names, schemas, and request mapping.
- `codex_plugin/blendex_mcp/server.py`: minimal stdio MCP server.
- `tests/codex_plugin/test_tools.py`: MCP tool mapping tests.
- `scripts/run_unit_tests.sh`: unit test convenience script.
- `scripts/run_blender_smoke.py`: Blender background smoke test launcher.
- `tests/integration/blender_smoke.py`: Blender-side smoke test script.

---

### Task 1: Shared Protocol Package

**Files:**
- Create: `pyproject.toml`
- Create: `src/blendex_protocol/__init__.py`
- Create: `src/blendex_protocol/errors.py`
- Create: `src/blendex_protocol/messages.py`
- Create: `src/blendex_protocol/validation.py`
- Create: `tests/protocol/test_messages.py`
- Create: `tests/protocol/test_validation.py`

- [ ] **Step 1: Write failing protocol tests**

Create `tests/protocol/test_messages.py`:

```python
import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest, OperationResponse


class OperationMessageTests(unittest.TestCase):
    def test_request_round_trips_from_dict(self):
        payload = {
            "id": "req_1",
            "type": "geometry_nodes.create_node",
            "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            "params": {"node_type": "GeometryNodeJoinGeometry", "label": "Join"},
        }

        request = OperationRequest.from_dict(payload)

        self.assertEqual(request.id, "req_1")
        self.assertEqual(request.type, "geometry_nodes.create_node")
        self.assertEqual(request.target["object_id"], "Cube")
        self.assertEqual(request.to_dict(), payload)

    def test_error_response_shape(self):
        error = BlendexError(
            code="NODE_TYPE_NOT_FOUND",
            message="Node type is unavailable.",
            retry_hint="Refresh capabilities.",
        )

        response = OperationResponse.error("req_2", error)

        self.assertFalse(response.ok)
        self.assertEqual(response.id, "req_2")
        self.assertEqual(response.error["code"], "NODE_TYPE_NOT_FOUND")
        self.assertEqual(response.error["retry_hint"], "Refresh capabilities.")


if __name__ == "__main__":
    unittest.main()
```

Create `tests/protocol/test_validation.py`:

```python
import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


class ValidationTests(unittest.TestCase):
    def test_rejects_unknown_operation(self):
        request = OperationRequest(
            id="req_bad",
            type="python.exec",
            target={},
            params={"code": "print('blocked')"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "UNSUPPORTED_OPERATION")

    def test_accepts_create_node_request(self):
        request = OperationRequest(
            id="req_ok",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry"},
        )

        validate_request(request)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.protocol.test_messages tests.protocol.test_validation -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'blendex_protocol'`.

- [ ] **Step 3: Add package config and protocol implementation**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "blendex"
version = "0.1.0"
description = "CodeX to Blender Geometry Nodes bridge"
requires-python = ">=3.9"

[tool.setuptools.packages.find]
where = ["src"]
```

Create `src/blendex_protocol/errors.py`:

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional


ERROR_CODES = {
    "BLENDER_NOT_CONNECTED",
    "AUTH_REQUIRED",
    "UNSUPPORTED_OPERATION",
    "OBJECT_NOT_FOUND",
    "OBJECT_NOT_SELECTED",
    "MODIFIER_NOT_FOUND",
    "NODE_TREE_NOT_FOUND",
    "NODE_TYPE_NOT_FOUND",
    "SOCKET_NOT_FOUND",
    "SOCKET_TYPE_MISMATCH",
    "LINK_NOT_ALLOWED",
    "VALUE_TYPE_MISMATCH",
    "OWNERSHIP_REQUIRED",
    "VALIDATION_FAILED",
    "EXECUTION_FAILED",
}


@dataclass
class BlendexError(Exception):
    code: str
    message: str
    retry_hint: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError(f"Unknown BlendeX error code: {self.code}")
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.retry_hint:
            data["retry_hint"] = self.retry_hint
        if self.details:
            data["details"] = self.details
        return data
```

Create `src/blendex_protocol/messages.py`:

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .errors import BlendexError


@dataclass
class OperationRequest:
    id: str
    type: str
    target: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "OperationRequest":
        request_id = payload.get("id")
        request_type = payload.get("type")
        if not isinstance(request_id, str) or not request_id:
            raise BlendexError("VALIDATION_FAILED", "Request id must be a non-empty string.")
        if not isinstance(request_type, str) or not request_type:
            raise BlendexError("VALIDATION_FAILED", "Request type must be a non-empty string.")
        target = payload.get("target", {})
        params = payload.get("params", {})
        if not isinstance(target, dict):
            raise BlendexError("VALIDATION_FAILED", "Request target must be an object.")
        if not isinstance(params, dict):
            raise BlendexError("VALIDATION_FAILED", "Request params must be an object.")
        return cls(id=request_id, type=request_type, target=target, params=params)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "params": self.params,
        }


@dataclass
class OperationResponse:
    id: str
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    @classmethod
    def success(cls, request_id: str, result: Optional[Dict[str, Any]] = None) -> "OperationResponse":
        return cls(id=request_id, ok=True, result=result or {})

    @classmethod
    def error(cls, request_id: str, error: BlendexError) -> "OperationResponse":
        return cls(id=request_id, ok=False, error=error.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"id": self.id, "ok": self.ok}
        if self.ok:
            data["result"] = self.result or {}
        else:
            data["error"] = self.error or {}
        return data
```

Create `src/blendex_protocol/validation.py`:

```python
from typing import Set

from .errors import BlendexError
from .messages import OperationRequest


ALLOWED_OPERATIONS: Set[str] = {
    "scene.inspect",
    "scene.get_selected_object",
    "scene.create_carrier_mesh",
    "scene.list_modifiers",
    "capabilities.scan",
    "capabilities.supported_operations",
    "geometry_nodes.create_modifier",
    "geometry_nodes.inspect_tree",
    "geometry_nodes.create_node",
    "geometry_nodes.link_sockets",
    "geometry_nodes.set_socket_value",
    "geometry_nodes.label_node",
    "geometry_nodes.mark_ownership",
    "safety.validate_batch",
    "safety.dry_run",
    "safety.undo_last_batch",
    "safety.check_ownership",
}


def validate_request(request: OperationRequest) -> None:
    if request.type not in ALLOWED_OPERATIONS:
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Operation is not allowlisted: {request.type}",
            retry_hint="Choose a supported BlendeX structured operation.",
        )
    if request.type.startswith("geometry_nodes.") and "object_id" not in request.target:
        raise BlendexError(
            "VALIDATION_FAILED",
            "Geometry Nodes operations require target.object_id.",
            retry_hint="Inspect the scene or create a carrier mesh before editing nodes.",
        )
    if request.type == "geometry_nodes.create_node" and "node_type" not in request.params:
        raise BlendexError(
            "VALIDATION_FAILED",
            "create_node requires params.node_type.",
            retry_hint="Use a node type returned by capabilities.scan.",
        )
```

Create `src/blendex_protocol/__init__.py`:

```python
from .errors import BlendexError
from .messages import OperationRequest, OperationResponse
from .validation import ALLOWED_OPERATIONS, validate_request

__all__ = [
    "ALLOWED_OPERATIONS",
    "BlendexError",
    "OperationRequest",
    "OperationResponse",
    "validate_request",
]
```

- [ ] **Step 4: Run protocol tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.protocol.test_messages tests.protocol.test_validation -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/blendex_protocol tests/protocol
git commit -m "feat: add shared BlendeX protocol"
```

---

### Task 2: Blender Add-on Shell, State, Logs, and UI

**Files:**
- Create: `blender_addon/blendex/__init__.py`
- Create: `blender_addon/blendex/state.py`
- Create: `blender_addon/blendex/logs.py`
- Create: `blender_addon/blendex/ui.py`
- Create: `tests/blender_addon/test_state.py`

- [ ] **Step 1: Write failing state tests**

Create `tests/blender_addon/test_state.py`:

```python
import unittest

from blender_addon.blendex.logs import OperationLog
from blender_addon.blendex.state import BlendexState


class BlendexStateTests(unittest.TestCase):
    def test_records_recent_operations(self):
        state = BlendexState()
        state.record(OperationLog(request_id="req_1", operation="scene.inspect", ok=True, message="Scene inspected."))

        self.assertEqual(len(state.recent_logs), 1)
        self.assertEqual(state.recent_logs[0].operation, "scene.inspect")
        self.assertTrue(state.recent_logs[0].ok)

    def test_connection_fields_have_safe_defaults(self):
        state = BlendexState()

        self.assertFalse(state.service_running)
        self.assertFalse(state.client_connected)
        self.assertEqual(state.port, 8765)
        self.assertGreaterEqual(len(state.session_token), 16)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_state -v
```

Expected: FAIL with `ModuleNotFoundError` for `blender_addon.blendex`.

- [ ] **Step 3: Add add-on state and log model**

Create `blender_addon/blendex/logs.py`:

```python
from dataclasses import dataclass
from time import time
from typing import Optional


@dataclass
class OperationLog:
    request_id: str
    operation: str
    ok: bool
    message: str
    timestamp: float = 0.0
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time()
```

Create `blender_addon/blendex/state.py`:

```python
import secrets
from dataclasses import dataclass, field
from typing import List

from .logs import OperationLog


@dataclass
class BlendexState:
    port: int = 8765
    service_running: bool = False
    client_connected: bool = False
    session_token: str = field(default_factory=lambda: secrets.token_urlsafe(18))
    recent_logs: List[OperationLog] = field(default_factory=list)
    max_logs: int = 50

    def record(self, log: OperationLog) -> None:
        self.recent_logs.insert(0, log)
        del self.recent_logs[self.max_logs :]


STATE = BlendexState()
```

- [ ] **Step 4: Add Blender registration shell and UI panel**

Create `blender_addon/blendex/ui.py`:

```python
from .state import STATE


class BLENDEX_PT_panel:
    bl_label = "BlendeX"
    bl_idname = "BLENDEX_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BlendeX"

    def draw(self, context):
        layout = self.layout
        status = "Running" if STATE.service_running else "Stopped"
        connected = "Connected" if STATE.client_connected else "No CodeX client"
        layout.label(text=f"Service: {status}")
        layout.label(text=f"Client: {connected}")
        layout.label(text=f"Port: {STATE.port}")
        layout.label(text=f"Token: {STATE.session_token[:6]}...")
        layout.operator("blendex.start_service", text="Start Service")
        layout.operator("blendex.stop_service", text="Stop Service")
        layout.separator()
        layout.label(text="Recent Operations")
        for log in STATE.recent_logs[:8]:
            icon = "CHECKMARK" if log.ok else "ERROR"
            layout.label(text=f"{log.operation}: {log.message}", icon=icon)


def panel_classes():
    return [BLENDEX_PT_panel]
```

Create `blender_addon/blendex/__init__.py`:

```python
bl_info = {
    "name": "BlendeX",
    "author": "BlendeX Contributors",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BlendeX",
    "description": "CodeX bridge for structured Geometry Nodes operations",
    "category": "Node",
}


def _load_classes():
    from .ui import panel_classes

    return panel_classes()


def register():
    import bpy

    for cls in _load_classes():
        bpy.utils.register_class(cls)


def unregister():
    import bpy

    for cls in reversed(_load_classes()):
        bpy.utils.unregister_class(cls)
```

- [ ] **Step 5: Run state tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_state -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add blender_addon/blendex tests/blender_addon/test_state.py
git commit -m "feat: add Blender add-on shell"
```

---

### Task 3: Safe Executor With Fake Blender Tests

**Files:**
- Create: `blender_addon/blendex/executor.py`
- Create: `tests/blender_addon/test_executor_fake.py`

- [ ] **Step 1: Write failing executor tests**

Create `tests/blender_addon/test_executor_fake.py`:

```python
import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blender_addon.blendex.executor import GeometryNodesExecutor


class FakeNodeTree:
    def __init__(self):
        self.nodes = {}
        self.links = []


class FakeModifier:
    def __init__(self, name):
        self.name = name
        self.type = "NODES"
        self.node_group = FakeNodeTree()
        self["blendex_owned"] = True
        self.props = {}

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]


class FakeObject:
    def __init__(self, name):
        self.name = name
        self.modifiers = {"BlendeX Geometry": FakeModifier("BlendeX Geometry")}


class FakeContext:
    def __init__(self):
        self.objects = {"Cube": FakeObject("Cube")}
        self.node_types = {"GeometryNodeJoinGeometry"}


class ExecutorTests(unittest.TestCase):
    def test_create_node_adds_node_to_tree(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_1",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry", "label": "Join Geometry"},
        )

        result = executor.execute(request)

        self.assertEqual(result["node_type"], "GeometryNodeJoinGeometry")
        self.assertEqual(result["label"], "Join Geometry")

    def test_create_node_rejects_unavailable_type(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_2",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeUnknown"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "NODE_TYPE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_executor_fake -v
```

Expected: FAIL with `ModuleNotFoundError` for `blender_addon.blendex.executor`.

- [ ] **Step 3: Implement minimal safe executor**

Create `blender_addon/blendex/executor.py`:

```python
from typing import Any, Dict

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


class GeometryNodesExecutor:
    def __init__(self, context: Any):
        self.context = context

    def execute(self, request: OperationRequest) -> Dict[str, Any]:
        validate_request(request)
        if request.type == "geometry_nodes.create_node":
            return self._create_node(request)
        if request.type == "geometry_nodes.inspect_tree":
            return self._inspect_tree(request)
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Executor does not implement operation: {request.type}",
            retry_hint="Call capabilities.supported_operations before planning.",
        )

    def _object(self, object_id: str) -> Any:
        obj = self.context.objects.get(object_id)
        if obj is None:
            raise BlendexError("OBJECT_NOT_FOUND", f"Object not found: {object_id}")
        return obj

    def _modifier(self, obj: Any, modifier_id: str) -> Any:
        modifier = obj.modifiers.get(modifier_id)
        if modifier is None:
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier not found: {modifier_id}")
        if getattr(modifier, "type", "") != "NODES":
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier is not a Geometry Nodes modifier: {modifier_id}")
        return modifier

    def _create_node(self, request: OperationRequest) -> Dict[str, Any]:
        node_type = request.params["node_type"]
        if node_type not in self.context.node_types:
            raise BlendexError(
                "NODE_TYPE_NOT_FOUND",
                f"Node type is unavailable: {node_type}",
                retry_hint="Refresh capabilities and choose a node type reported by Blender.",
            )
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        tree = self._node_tree(modifier)
        label = request.params.get("label", node_type)
        location = request.params.get("location", [0, 0])
        if hasattr(tree.nodes, "new"):
            node = tree.nodes.new(type=node_type)
            node.label = label
            node.location = location
            return {"id": node.name, "node_type": node_type, "label": label, "location": list(location)}
        node_id = f"node_{len(tree.nodes) + 1}"
        node_data = {"id": node_id, "node_type": node_type, "label": label, "location": location}
        tree.nodes[node_id] = node_data
        return node_data

    def _inspect_tree(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        tree = self._node_tree(modifier)
        if hasattr(tree.nodes, "values"):
            nodes = list(tree.nodes.values())
        else:
            nodes = [{"id": node.name, "node_type": node.bl_idname, "label": node.label} for node in tree.nodes]
        return {"nodes": nodes, "links": [str(link) for link in tree.links]}

    def _node_tree(self, modifier: Any) -> Any:
        tree = getattr(modifier, "node_group", None)
        if tree is not None:
            return tree
        try:
            import bpy

            tree = bpy.data.node_groups.new(f"{modifier.name} Node Tree", "GeometryNodeTree")
            modifier.node_group = tree
            return tree
        except Exception as exc:
            raise BlendexError(
                "NODE_TREE_NOT_FOUND",
                f"Could not create or access Geometry Nodes tree for modifier: {modifier.name}",
                details={"exception": str(exc)},
            )
```

- [ ] **Step 4: Run executor tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_executor_fake -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add blender_addon/blendex/executor.py tests/blender_addon/test_executor_fake.py
git commit -m "feat: add safe Geometry Nodes executor"
```

---

### Task 4: Capability Scanner

**Files:**
- Create: `blender_addon/blendex/capabilities.py`
- Create: `tests/blender_addon/test_capabilities_fake.py`

- [ ] **Step 1: Write failing capability tests**

Create `tests/blender_addon/test_capabilities_fake.py`:

```python
import unittest

from blender_addon.blendex.capabilities import scan_capabilities


class FakeBlender:
    version = (4, 1, 0)
    node_types = {
        "GeometryNodeJoinGeometry": {"inputs": ["Geometry"], "outputs": ["Geometry"]},
        "GeometryNodeInstanceOnPoints": {"inputs": ["Points", "Instance"], "outputs": ["Instances"]},
    }


class CapabilityTests(unittest.TestCase):
    def test_scan_returns_version_and_node_types(self):
        result = scan_capabilities(FakeBlender())

        self.assertEqual(result["blender_version"], [4, 1, 0])
        self.assertIn("GeometryNodeJoinGeometry", result["node_types"])
        self.assertEqual(result["supported_operations"][0], "capabilities.scan")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_capabilities_fake -v
```

Expected: FAIL with `ModuleNotFoundError` for `capabilities`.

- [ ] **Step 3: Implement scanner**

Create `blender_addon/blendex/capabilities.py`:

```python
from typing import Any, Dict

from blendex_protocol.validation import ALLOWED_OPERATIONS


def scan_capabilities(runtime: Any) -> Dict[str, Any]:
    version = list(getattr(runtime, "version", (0, 0, 0)))
    node_types = getattr(runtime, "node_types", {})
    return {
        "blender_version": version,
        "node_types": node_types,
        "supported_operations": sorted(ALLOWED_OPERATIONS),
    }


def scan_bpy_capabilities() -> Dict[str, Any]:
    import bpy

    node_types: Dict[str, Dict[str, Any]] = {}
    for subclass in bpy.types.GeometryNode.__subclasses__():
        identifier = getattr(subclass, "__name__", "")
        if identifier.startswith("GeometryNode"):
            node_types[identifier] = {"inputs": [], "outputs": []}
    runtime = type("BpyRuntime", (), {"version": bpy.app.version, "node_types": node_types})()
    return scan_capabilities(runtime)
```

- [ ] **Step 4: Run capability tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_capabilities_fake -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add blender_addon/blendex/capabilities.py tests/blender_addon/test_capabilities_fake.py
git commit -m "feat: add runtime capability scanner"
```

---

### Task 5: Local WebSocket Service in Blender Add-on

**Files:**
- Create: `blender_addon/blendex/server.py`
- Modify: `blender_addon/blendex/__init__.py`
- Create: `tests/blender_addon/test_server_dispatch.py`

- [ ] **Step 1: Write failing dispatch tests**

Create `tests/blender_addon/test_server_dispatch.py`:

```python
import unittest

from blender_addon.blendex.server import dispatch_payload


class DispatchTests(unittest.TestCase):
    def test_dispatch_rejects_unknown_operation_as_json_response(self):
        response = dispatch_payload(
            {
                "id": "req_bad",
                "type": "python.exec",
                "target": {},
                "params": {"code": "print('blocked')"},
            },
            executor=None,
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "UNSUPPORTED_OPERATION")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_server_dispatch -v
```

Expected: FAIL with `ModuleNotFoundError` for `server`.

- [ ] **Step 3: Implement dispatch and service controls**

Create `blender_addon/blendex/server.py`:

```python
import base64
import hashlib
import json
import socket
import struct
import threading
from typing import Any, Dict, Optional

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest, OperationResponse
from blendex_protocol.validation import validate_request

from .logs import OperationLog
from .state import STATE


_server_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def dispatch_payload(payload: Dict[str, Any], executor: Any) -> Dict[str, Any]:
    request_id = str(payload.get("id", "unknown"))
    try:
        request = OperationRequest.from_dict(payload)
        validate_request(request)
        if executor is None:
            result = {"validated": True}
        else:
            result = executor.execute(request)
        STATE.record(OperationLog(request_id=request.id, operation=request.type, ok=True, message="OK"))
        return OperationResponse.success(request.id, result).to_dict()
    except BlendexError as error:
        STATE.record(OperationLog(request_id=request_id, operation=str(payload.get("type", "")), ok=False, message=error.message, error_code=error.code))
        return OperationResponse.error(request_id, error).to_dict()


def start_service(port: Optional[int] = None) -> None:
    global _server_thread
    if STATE.service_running:
        return
    if port is not None:
        STATE.port = port
    _stop_event.clear()
    _server_thread = threading.Thread(target=_run_socket_server, daemon=True)
    _server_thread.start()
    STATE.service_running = True


def stop_service() -> None:
    _stop_event.set()
    STATE.service_running = False
    STATE.client_connected = False


def _default_executor() -> Any:
    import bpy

    from .capabilities import scan_bpy_capabilities
    from .executor import GeometryNodesExecutor

    capabilities = scan_bpy_capabilities()

    class BpyExecutionContext:
        objects = bpy.data.objects
        node_types = set(capabilities["node_types"].keys())

    return GeometryNodesExecutor(BpyExecutionContext())


def _websocket_accept_key(client_key: str) -> str:
    websocket_guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    digest = hashlib.sha1((client_key + websocket_guid).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def _read_http_headers(conn: socket.socket) -> Dict[str, str]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(1024)
        if not chunk:
            break
        data += chunk
    lines = data.decode("utf-8").split("\r\n")
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return headers


def _send_handshake(conn: socket.socket, headers: Dict[str, str]) -> None:
    key = headers.get("sec-websocket-key")
    if not key:
        raise BlendexError("AUTH_REQUIRED", "Missing WebSocket key.")
    accept = _websocket_accept_key(key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    )
    conn.sendall(response.encode("utf-8"))


def _read_exact(conn: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError("WebSocket connection closed.")
        data += chunk
    return data


def _read_ws_text(conn: socket.socket) -> Optional[str]:
    first, second = _read_exact(conn, 2)
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if opcode == 0x8:
        return None
    if length == 126:
        length = struct.unpack("!H", _read_exact(conn, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _read_exact(conn, 8))[0]
    mask = _read_exact(conn, 4) if masked else b""
    payload = bytearray(_read_exact(conn, length))
    if masked:
        for index in range(length):
            payload[index] ^= mask[index % 4]
    return payload.decode("utf-8")


def _send_ws_text(conn: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    header = bytearray([0x81])
    length = len(payload)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(127)
        header.extend(struct.pack("!Q", length))
    conn.sendall(bytes(header) + payload)


def _run_socket_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", STATE.port))
        server.listen(1)
        server.settimeout(0.25)
        while not _stop_event.is_set():
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue
            with conn:
                STATE.client_connected = True
                headers = _read_http_headers(conn)
                _send_handshake(conn, headers)
                while not _stop_event.is_set():
                    text = _read_ws_text(conn)
                    if text is None:
                        break
                    payload = json.loads(text)
                    response = dispatch_payload(payload, executor=_default_executor())
                    _send_ws_text(conn, json.dumps(response))
                STATE.client_connected = False
```

Modify `blender_addon/blendex/__init__.py` to register start/stop operators:

```python
bl_info = {
    "name": "BlendeX",
    "author": "BlendeX Contributors",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BlendeX",
    "description": "CodeX bridge for structured Geometry Nodes operations",
    "category": "Node",
}


def _load_classes():
    import bpy
    from . import server
    from .ui import panel_classes

    class BLENDEX_OT_start_service(bpy.types.Operator):
        bl_idname = "blendex.start_service"
        bl_label = "Start BlendeX Service"

        def execute(self, context):
            server.start_service()
            return {"FINISHED"}

    class BLENDEX_OT_stop_service(bpy.types.Operator):
        bl_idname = "blendex.stop_service"
        bl_label = "Stop BlendeX Service"

        def execute(self, context):
            server.stop_service()
            return {"FINISHED"}

    return [BLENDEX_OT_start_service, BLENDEX_OT_stop_service] + panel_classes()


def register():
    import bpy

    for cls in _load_classes():
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    from . import server

    server.stop_service()
    for cls in reversed(_load_classes()):
        bpy.utils.unregister_class(cls)
```

- [ ] **Step 4: Run dispatch tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.blender_addon.test_server_dispatch -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add blender_addon/blendex/server.py blender_addon/blendex/__init__.py tests/blender_addon/test_server_dispatch.py
git commit -m "feat: add local Blender service dispatch"
```

---

### Task 6: CodeX Plugin Manifest and MCP Tool Mapping

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `.mcp.json`
- Create: `codex_plugin/blendex_mcp/__init__.py`
- Create: `codex_plugin/blendex_mcp/catalog.py`
- Create: `codex_plugin/blendex_mcp/tools.py`
- Create: `tests/codex_plugin/test_tools.py`

- [ ] **Step 1: Write failing tool mapping tests**

Create `tests/codex_plugin/test_tools.py`:

```python
import unittest

from codex_plugin.blendex_mcp.tools import tool_names, tool_to_operation


class ToolMappingTests(unittest.TestCase):
    def test_tool_names_include_core_graph_tools(self):
        names = tool_names()

        self.assertIn("blendex_create_node", names)
        self.assertIn("blendex_scan_capabilities", names)

    def test_create_node_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_create_node",
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "node_type": "GeometryNodeJoinGeometry",
                "label": "Join",
            },
            request_id="req_1",
        )

        self.assertEqual(operation["type"], "geometry_nodes.create_node")
        self.assertEqual(operation["target"]["object_id"], "Cube")
        self.assertEqual(operation["params"]["node_type"], "GeometryNodeJoinGeometry")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_tools -v
```

Expected: FAIL with `ModuleNotFoundError` for `codex_plugin.blendex_mcp`.

- [ ] **Step 3: Add plugin manifest and tool definitions**

Create `.codex-plugin/plugin.json`:

```json
{
  "name": "blendex",
  "version": "0.1.0",
  "description": "Connect CodeX to Blender Geometry Nodes through safe structured operations.",
  "author": {
    "name": "BlendeX Contributors"
  },
  "license": "MIT",
  "keywords": ["blender", "geometry-nodes", "codex", "procedural"],
  "mcpServers": "./.mcp.json",
  "interface": {
    "displayName": "BlendeX",
    "shortDescription": "Drive Blender Geometry Nodes from CodeX",
    "longDescription": "BlendeX lets CodeX connect to a local Blender add-on and create Geometry Nodes networks through structured, allowlisted operations.",
    "developerName": "BlendeX Contributors",
    "category": "Developer Tools",
    "capabilities": ["Read", "Write"],
    "defaultPrompt": [
      "Connect to Blender and inspect the current scene",
      "Create a simple procedural Geometry Nodes setup on the selected object"
    ],
    "brandColor": "#4C8BF5"
  }
}
```

Create `.mcp.json`:

```json
{
  "mcpServers": {
    "blendex": {
      "command": "python3",
      "args": ["-m", "codex_plugin.blendex_mcp.server"],
      "cwd": "."
    }
  }
}
```

Create `codex_plugin/blendex_mcp/__init__.py`:

```python
__all__ = []
```

Create `codex_plugin/blendex_mcp/catalog.py`:

```python
SEMANTIC_NODE_CATALOG = {
    "GeometryNodeJoinGeometry": {
        "role": "Combines multiple geometry streams into one output.",
        "common_use": "Merge generated pieces before sending to Group Output.",
    },
    "GeometryNodeInstanceOnPoints": {
        "role": "Places instances on point geometry.",
        "common_use": "Scatter plants, rocks, buildings, or repeated modules.",
    },
    "GeometryNodeRealizeInstances": {
        "role": "Converts instances into editable realized geometry.",
        "common_use": "Apply downstream mesh operations after instancing.",
    },
}
```

Create `codex_plugin/blendex_mcp/tools.py`:

```python
from typing import Any, Dict, List


TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "blendex_scan_capabilities",
        "description": "Scan the connected Blender runtime for supported Geometry Nodes capabilities.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "blendex_inspect_scene",
        "description": "Inspect the current Blender scene and selected object.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "blendex_create_node",
        "description": "Create a Geometry Nodes node on a target object and modifier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": {"type": "string"},
                "modifier_id": {"type": "string"},
                "node_type": {"type": "string"},
                "label": {"type": "string"},
            },
            "required": ["object_id", "node_type"],
            "additionalProperties": False,
        },
    },
]


def tool_names() -> List[str]:
    return [tool["name"] for tool in TOOL_DEFINITIONS]


def tool_to_operation(name: str, arguments: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    if name == "blendex_scan_capabilities":
        return {"id": request_id, "type": "capabilities.scan", "target": {}, "params": {}}
    if name == "blendex_inspect_scene":
        return {"id": request_id, "type": "scene.inspect", "target": {}, "params": {}}
    if name == "blendex_create_node":
        return {
            "id": request_id,
            "type": "geometry_nodes.create_node",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {
                "node_type": arguments["node_type"],
                "label": arguments.get("label", arguments["node_type"]),
            },
        }
    raise ValueError(f"Unknown BlendeX tool: {name}")
```

- [ ] **Step 4: Run tool mapping tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_tools -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .codex-plugin/plugin.json .mcp.json codex_plugin/blendex_mcp tests/codex_plugin/test_tools.py
git commit -m "feat: add CodeX plugin tool definitions"
```

---

### Task 7: MCP Server and Blender Client

**Files:**
- Create: `codex_plugin/blendex_mcp/blender_client.py`
- Create: `codex_plugin/blendex_mcp/server.py`
- Create: `tests/codex_plugin/test_blender_client.py`

- [ ] **Step 1: Write failing client test**

Create `tests/codex_plugin/test_blender_client.py`:

```python
import unittest

from codex_plugin.blendex_mcp.blender_client import BlenderConnectionConfig


class BlenderClientTests(unittest.TestCase):
    def test_default_config_points_to_local_service(self):
        config = BlenderConnectionConfig()

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8765)
        self.assertEqual(config.timeout_seconds, 5.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_blender_client -v
```

Expected: FAIL with `ModuleNotFoundError` for `blender_client`.

- [ ] **Step 3: Implement client and minimal MCP server**

Create `codex_plugin/blendex_mcp/blender_client.py`:

```python
import base64
import os
import json
import socket
import struct
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BlenderConnectionConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    timeout_seconds: float = 5.0


class BlenderClient:
    def __init__(self, config: BlenderConnectionConfig = BlenderConnectionConfig()):
        self.config = config

    def send_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        with socket.create_connection((self.config.host, self.config.port), timeout=self.config.timeout_seconds) as sock:
            self._handshake(sock)
            self._send_text(sock, json.dumps(operation))
            return json.loads(self._read_text(sock))

    def _handshake(self, sock: socket.socket) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET /blendex HTTP/1.1\r\n"
            f"Host: {self.config.host}:{self.config.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode("utf-8"))
        response = sock.recv(4096).decode("utf-8")
        if "101 Switching Protocols" not in response:
            raise ConnectionError("BlendeX service did not accept WebSocket handshake.")

    def _send_text(self, sock: socket.socket, text: str) -> None:
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        masked = bytearray(payload)
        for index in range(len(masked)):
            masked[index] ^= mask[index % 4]
        sock.sendall(bytes(header) + mask + bytes(masked))

    def _read_exact(self, sock: socket.socket, size: int) -> bytes:
        data = b""
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("BlendeX service closed the WebSocket connection.")
            data += chunk
        return data

    def _read_text(self, sock: socket.socket) -> str:
        first, second = self._read_exact(sock, 2)
        opcode = first & 0x0F
        length = second & 0x7F
        if opcode != 0x1:
            raise ConnectionError(f"Expected text WebSocket frame, got opcode {opcode}.")
        if length == 126:
            length = struct.unpack("!H", self._read_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(sock, 8))[0]
        return self._read_exact(sock, length).decode("utf-8")
```

Create `codex_plugin/blendex_mcp/server.py`:

```python
import json
import sys
import uuid
from typing import Any, Dict

from .blender_client import BlenderClient
from .tools import TOOL_DEFINITIONS, tool_to_operation


def _content(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def handle_message(message: Dict[str, Any], client: BlenderClient) -> Dict[str, Any]:
    method = message.get("method")
    message_id = message.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "blendex", "version": "0.1.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": TOOL_DEFINITIONS}}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        operation = tool_to_operation(name, arguments, request_id=f"req_{uuid.uuid4().hex[:12]}")
        result = client.send_operation(operation)
        return {"jsonrpc": "2.0", "id": message_id, "result": _content(result)}
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main() -> None:
    client = BlenderClient()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_message(json.loads(line), client)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run client tests and protocol tests**

Run:

```bash
PYTHONPATH=src:. python3 -m unittest tests.codex_plugin.test_blender_client tests.codex_plugin.test_tools -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add codex_plugin/blendex_mcp/blender_client.py codex_plugin/blendex_mcp/server.py tests/codex_plugin/test_blender_client.py
git commit -m "feat: add BlendeX MCP server"
```

---

### Task 8: Unit Test Runner and Blender Smoke Test Harness

**Files:**
- Create: `scripts/run_unit_tests.sh`
- Create: `scripts/run_blender_smoke.py`
- Create: `tests/integration/blender_smoke.py`
- Modify: `README.md`

- [ ] **Step 1: Add unit test runner**

Create `scripts/run_unit_tests.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src:. python3 -m unittest discover -s tests -v
```

Run:

```bash
chmod +x scripts/run_unit_tests.sh
./scripts/run_unit_tests.sh
```

Expected: PASS for all pure Python tests.

- [ ] **Step 2: Add Blender smoke script**

Create `tests/integration/blender_smoke.py`:

```python
import pathlib
import sys

import bpy

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "blender_addon"))

import blendex
from blendex.executor import GeometryNodesExecutor
from blendex_protocol.messages import OperationRequest

blendex.register()

bpy.ops.mesh.primitive_cube_add(size=2)
obj = bpy.context.object
modifier = obj.modifiers.new("BlendeX Geometry", "NODES")
modifier["blendex_owned"] = True

class SmokeContext:
    objects = {obj.name: obj}
    node_types = {"GeometryNodeJoinGeometry"}


request = OperationRequest(
    id="smoke_1",
    type="geometry_nodes.create_node",
    target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
    params={"node_type": "GeometryNodeJoinGeometry", "label": "Join Geometry"},
)

result = GeometryNodesExecutor(SmokeContext()).execute(request)
assert result["node_type"] == "GeometryNodeJoinGeometry"
blendex.unregister()
```

Create `scripts/run_blender_smoke.py`:

```python
import os
import pathlib
import subprocess
import sys


def main() -> int:
    blender = os.environ.get("BLENDER")
    if not blender:
        print("SKIP: set BLENDER=/path/to/blender to run the Blender smoke test")
        return 0
    script = pathlib.Path(__file__).resolve().parents[1] / "tests" / "integration" / "blender_smoke.py"
    completed = subprocess.run([blender, "--background", "--python", str(script)], check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Add README**

Create `README.md`:

```markdown
# BlendeX

BlendeX connects CodeX to Blender Geometry Nodes through a local, structured operation bridge.

## Development

Run pure Python tests:

```bash
./scripts/run_unit_tests.sh
```

Run the Blender smoke test when Blender is installed:

```bash
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender python3 scripts/run_blender_smoke.py
```

## MVP Safety Boundary

BlendeX does not execute arbitrary AI-generated Python. The CodeX plugin sends allowlisted structured operations to the Blender add-on, and the Blender add-on validates operations before mutating the scene.

## Manual Acceptance

1. Install `blender_addon/blendex` as a Blender add-on.
2. Add this repository as a CodeX plugin.
3. Start the BlendeX service in Blender.
4. Ask CodeX to inspect the Blender scene.
5. Ask CodeX to create a Geometry Nodes node on the selected object.
6. Confirm the Blender panel shows the operation log.
```

- [ ] **Step 4: Run full verification**

Run:

```bash
./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
```

Expected: unit tests PASS; Blender smoke test either PASS if `BLENDER` is set or prints `SKIP`.

- [ ] **Step 5: Commit**

```bash
git add scripts tests/integration README.md
git commit -m "test: add BlendeX verification harness"
```

---

### Task 9: Finish MVP Review

**Files:**
- Modify: `docs/superpowers/specs/2026-06-01-blendex-design.md` only if implementation reveals a necessary spec correction.
- Modify: `README.md` only if verification commands or install instructions differ from the implemented paths.

- [ ] **Step 1: Run all tests**

Run:

```bash
./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
git status --short
```

Expected: pure Python tests PASS; smoke test PASS or SKIP; git status shows only intentional changes.

- [ ] **Step 2: Confirm safety requirements**

Run:

```bash
rg -n "exec\\(|eval\\(|python\\.exec|subprocess" blender_addon codex_plugin src tests
```

Expected: no arbitrary Python execution path in `blender_addon`; `python.exec` appears only in tests that assert rejection.

- [ ] **Step 3: Confirm tool coverage**

Run:

```bash
PYTHONPATH=src:. python3 - <<'PY'
from codex_plugin.blendex_mcp.tools import tool_names
print("\\n".join(tool_names()))
PY
```

Expected output includes:

```text
blendex_scan_capabilities
blendex_inspect_scene
blendex_create_node
```

- [ ] **Step 4: Commit final docs correction if needed**

If Step 1 or Step 2 required documentation corrections, commit them:

```bash
git add README.md docs/superpowers/specs/2026-06-01-blendex-design.md
git commit -m "docs: align BlendeX MVP instructions"
```

Expected: no commit is created when no docs changed.
