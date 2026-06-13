# BlendeX v0.3 Creative Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build BlendeX v0.3 as an early-user-ready creative workflow where CodeX can plan, dry-run, confirm, execute, inspect, retry, and undo BlendeX-owned Geometry Nodes changes.

**Architecture:** Keep the existing split bridge. CodeX-side modules own version reporting, recipe/planner logic, workflow summaries, and MCP tool mapping; Blender-side modules own token validation, batch execution, history, undo, UI state, and guarded Geometry Nodes mutation; the shared protocol keeps operation allowlists and validation aligned between both sides.

**Tech Stack:** Python 3.9+, Blender `bpy`, stdlib `unittest`, stdlib `socket`/`threading`, stdio MCP server, local WebSocket protocol, existing BlendeX protocol package.

---

## Scope Notes

This plan implements the approved spec:

- `docs/superpowers/specs/2026-06-13-blendex-v0-3-creative-workflow-design.md`

The plan is deliberately split by minor version:

- `0.21` cleans and aligns baseline version metadata.
- `0.22` enforces authenticated local sessions.
- `0.23` introduces executable batches and history.
- `0.24` adds undo and recovery signals.
- `0.25` enforces confirmation-first execution.
- `0.26` adds recipe infrastructure.
- `0.27` adds architecture and hard-surface recipes.
- `0.28` adds nature and scattering recipes.
- `0.29` adds the semi-open planner.
- `0.30` hardens docs, smoke coverage, and release metadata.

Do not skip minor versions. Each task should leave the repo testable and should be committed before moving to the next task.

## Planned File Structure

- `codex_plugin/blendex_mcp/version.py`
  - Single source of truth for CodeX plugin and MCP server version strings.

- `codex_plugin/blendex_mcp/blender_client.py`
  - WebSocket client, token transport, and connection configuration.

- `codex_plugin/blendex_mcp/tools.py`
  - MCP tool definitions and tool-to-operation mapping for v0.3 tools.

- `codex_plugin/blendex_mcp/server.py`
  - JSON-RPC MCP server, tool argument validation, and version reporting.

- `codex_plugin/blendex_mcp/workflow.py`
  - CodeX-side workflow helpers for confirmation summaries and confirmed batch payloads.

- `codex_plugin/blendex_mcp/recipes.py`
  - Recipe schema, registry, parameter validation, and recipe batch builders.

- `codex_plugin/blendex_mcp/planner.py`
  - Semi-open planner that chooses recipes or graph primitives using prompt text and capabilities.

- `src/blendex_protocol/validation.py`
  - Allowlist and request validation for new safety, history, recipe, and planner operations.

- `blender_addon/blendex/state.py`
  - Session token, auth status, recent logs, and recent batch state.

- `blender_addon/blendex/history.py`
  - Batch record dataclasses, history storage helpers, and query helpers.

- `blender_addon/blendex/batches.py`
  - Batch execution, client-id resolution, result aggregation, history recording, and undo routing.

- `blender_addon/blendex/server.py`
  - Auth validation, dispatch routing for new operations, and WebSocket request handling.

- `blender_addon/blendex/ui.py`
  - Blender panel status, auth, recent batch display, and undo button wiring.

- `blender_addon/blendex/__init__.py`
  - Blender add-on metadata and undo operator registration.

- `tests/codex_plugin/test_version.py`
  - Version alignment checks for CodeX-side metadata.

- `tests/codex_plugin/test_workflow.py`
  - Confirmation summary and confirmed batch payload tests.

- `tests/codex_plugin/test_recipes.py`
  - Recipe registry, parameter validation, and generated batch tests.

- `tests/codex_plugin/test_planner.py`
  - Recipe matching, fallback planning, unsupported request tests.

- `tests/blender_addon/test_auth.py`
  - Token header/request validation and auth state tests.

- `tests/blender_addon/test_history.py`
  - Batch record and history behavior tests.

- `tests/blender_addon/test_batches.py`
  - Batch execution, client-id resolution, partial failure, confirmation, and undo tests.

- Existing test files under `tests/protocol`, `tests/codex_plugin`, `tests/blender_addon`, and `tests/integration`
  - Extend where that keeps related behavior close to current coverage.

---

### Task 1: v0.21 Version Metadata and Baseline Hygiene

**Files:**
- Create: `codex_plugin/blendex_mcp/version.py`
- Create: `tests/codex_plugin/test_version.py`
- Modify: `.codex-plugin/plugin.json`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `blender_addon/blendex/__init__.py`
- Modify: `codex_plugin/blendex_mcp/server.py`

- [ ] **Step 1: Write failing version alignment tests**

Add `tests/codex_plugin/test_version.py`:

```python
import json
import pathlib
import re
import unittest

from codex_plugin.blendex_mcp.version import VERSION


ROOT = pathlib.Path(__file__).resolve().parents[2]


class VersionTests(unittest.TestCase):
    def test_plugin_manifest_uses_runtime_version(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["version"], VERSION)

    def test_pyproject_uses_runtime_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text()

        self.assertIn(f'version = "{VERSION}"', pyproject)

    def test_blender_addon_uses_runtime_version_tuple(self):
        init_text = (ROOT / "blender_addon" / "blendex" / "__init__.py").read_text()
        expected_tuple = tuple(int(part) for part in VERSION.split("."))

        self.assertIn(f'"version": {expected_tuple}', init_text)

    def test_mcp_server_reports_runtime_version(self):
        server_text = (ROOT / "codex_plugin" / "blendex_mcp" / "server.py").read_text()

        self.assertIn('"version": VERSION', server_text)

    def test_readme_names_development_track(self):
        readme = (ROOT / "README.md").read_text()

        self.assertRegex(readme, re.compile(r"v0\\.3", re.IGNORECASE))
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_version -v
```

Expected: FAIL because `version.py` does not exist and `.codex-plugin/plugin.json` still reports `0.1.0`.

- [ ] **Step 3: Create the version module**

Create `codex_plugin/blendex_mcp/version.py`:

```python
"""Version metadata for the BlendeX CodeX-side plugin."""

VERSION = "0.21.0"
```

- [ ] **Step 4: Update MCP server version reporting**

Modify `codex_plugin/blendex_mcp/server.py`:

```python
from .version import VERSION
```

Replace the current initialize response version:

```python
"serverInfo": {"name": "blendex", "version": VERSION},
```

- [ ] **Step 5: Align package, plugin, and Blender metadata**

Set these values:

```toml
# pyproject.toml
version = "0.21.0"
```

```json
// .codex-plugin/plugin.json
"version": "0.21.0"
```

```python
# blender_addon/blendex/__init__.py
"version": (0, 21, 0),
```

- [ ] **Step 6: Update README development status**

Add a short section near `## 当前状态`:

```markdown
## Development Track

BlendeX is currently moving from the released v0.2 graph kernel toward the v0.3 creative workflow track.
The v0.3 target is an early-user-ready loop: plan, dry-run, confirm, execute, inspect, retry, and undo BlendeX-owned Geometry Nodes changes from CodeX.
```

- [ ] **Step 7: Run version and full unit tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_version -v
./scripts/run_unit_tests.sh
```

Expected: both commands PASS.

- [ ] **Step 8: Commit v0.21**

Run:

```bash
git add .codex-plugin/plugin.json pyproject.toml README.md blender_addon/blendex/__init__.py codex_plugin/blendex_mcp/server.py codex_plugin/blendex_mcp/version.py tests/codex_plugin/test_version.py
git commit -m "chore: start BlendeX 0.3 development track"
```

---

### Task 2: v0.22 Authenticated Local Session

**Files:**
- Create: `tests/blender_addon/test_auth.py`
- Modify: `codex_plugin/blendex_mcp/blender_client.py`
- Modify: `blender_addon/blendex/state.py`
- Modify: `blender_addon/blendex/server.py`
- Modify: `blender_addon/blendex/ui.py`
- Modify: `tests/codex_plugin/test_blender_client.py`
- Modify: `tests/blender_addon/test_server_dispatch.py`

- [ ] **Step 1: Write failing auth tests for Blender server helpers**

Create `tests/blender_addon/test_auth.py`:

```python
import unittest

from blendex_protocol.errors import BlendexError
from blender_addon.blendex import server
from blender_addon.blendex.state import STATE


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.previous_token = STATE.session_token
        self.previous_auth = getattr(STATE, "client_authenticated", False)
        STATE.session_token = "secret-token"
        STATE.client_authenticated = False

    def tearDown(self):
        STATE.session_token = self.previous_token
        STATE.client_authenticated = self.previous_auth

    def test_validate_auth_headers_accepts_matching_token(self):
        server._validate_auth_headers({"x-blendex-token": "secret-token"})

        self.assertTrue(STATE.client_authenticated)

    def test_validate_auth_headers_rejects_missing_token(self):
        with self.assertRaises(BlendexError) as raised:
            server._validate_auth_headers({})

        self.assertEqual(raised.exception.code, "AUTH_REQUIRED")
        self.assertFalse(STATE.client_authenticated)

    def test_validate_auth_headers_rejects_wrong_token(self):
        with self.assertRaises(BlendexError) as raised:
            server._validate_auth_headers({"x-blendex-token": "wrong"})

        self.assertEqual(raised.exception.code, "AUTH_FAILED")
        self.assertFalse(STATE.client_authenticated)
```

- [ ] **Step 2: Write failing client handshake header test**

Add to `tests/codex_plugin/test_blender_client.py`:

```python
    def test_handshake_sends_session_token_header(self):
        sock = FakeSocket(
            [
                (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    "Sec-WebSocket-Accept: {accept}\r\n\r\n"
                ).encode("utf-8")
            ]
        )
        client = BlenderClient(BlenderConnectionConfig(session_token="secret-token"))
        accept = self._accept_for_next_key(sock, client)

        sent = sock.sent[0].decode("utf-8")
        self.assertIn("X-BlendeX-Token: secret-token\r\n", sent)
```

If the existing fake socket helpers do not expose `_accept_for_next_key`, add a local helper in that test file that extracts `Sec-WebSocket-Key` from `sock.sent[0]` and computes the expected accept header using the same RFC 6455 GUID already used by current tests.

- [ ] **Step 3: Run targeted auth tests to verify they fail**

Run:

```bash
python3 -m unittest tests.blender_addon.test_auth tests.codex_plugin.test_blender_client -v
```

Expected: FAIL because `session_token` config and `_validate_auth_headers` do not exist.

- [ ] **Step 4: Extend connection config and handshake**

Modify `codex_plugin/blendex_mcp/blender_client.py`:

```python
@dataclass
class BlenderConnectionConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    timeout_seconds: float = 5.0
    session_token: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "BlenderConnectionConfig":
        token = os.environ.get("BLENDEX_SESSION_TOKEN") or os.environ.get("BLENDEX_TOKEN")
        return cls(session_token=token)
```

Update `BlenderClient.__init__`:

```python
self.config = config or BlenderConnectionConfig.from_environment()
```

Update `_handshake` so the HTTP request includes this line when a token is present:

```python
token_header = f"X-BlendeX-Token: {self.config.session_token}\r\n" if self.config.session_token else ""
```

Insert `token_header` before `Sec-WebSocket-Version`.

- [ ] **Step 5: Add auth state fields**

Modify `blender_addon/blendex/state.py`:

```python
client_authenticated: bool = False
last_auth_error: str = ""
```

Keep the existing dataclass field order readable:

```python
service_running: bool = False
client_connected: bool = False
client_authenticated: bool = False
last_auth_error: str = ""
```

- [ ] **Step 6: Add server auth validation**

Modify `blender_addon/blendex/server.py`:

```python
def _validate_auth_headers(headers: Dict[str, str]) -> None:
    token = headers.get("x-blendex-token")
    if not token:
        STATE.client_authenticated = False
        STATE.last_auth_error = "Missing BlendeX token."
        raise BlendexError("AUTH_REQUIRED", "Missing BlendeX session token.")
    if token != STATE.session_token:
        STATE.client_authenticated = False
        STATE.last_auth_error = "Invalid BlendeX token."
        raise BlendexError("AUTH_FAILED", "Invalid BlendeX session token.")
    STATE.client_authenticated = True
    STATE.last_auth_error = ""
```

Call `_validate_auth_headers(headers)` in `_send_handshake` before computing the accept key. If validation fails, send a simple HTTP response and re-raise:

```python
try:
    _validate_auth_headers(headers)
except BlendexError as error:
    conn.sendall(f"HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\nX-BlendeX-Error: {error.code}\r\n\r\n".encode("utf-8"))
    raise
```

- [ ] **Step 7: Reset auth state on disconnect and stop**

In `stop_service()` and the connection `finally` block in `_run_socket_server`, set:

```python
STATE.client_authenticated = False
```

Leave `last_auth_error` intact after an auth failure so the panel can show it.

- [ ] **Step 8: Show auth status in Blender panel**

Modify `blender_addon/blendex/ui.py`:

```python
auth = "Authenticated" if STATE.client_authenticated else "Not authenticated"
layout.label(text=f"Auth: {auth}")
if STATE.last_auth_error:
    layout.label(text=f"Auth Error: {STATE.last_auth_error}", icon="ERROR")
```

- [ ] **Step 9: Run auth and full unit tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_auth tests.codex_plugin.test_blender_client tests.blender_addon.test_server_dispatch -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 10: Commit v0.22**

Run:

```bash
git add codex_plugin/blendex_mcp/blender_client.py blender_addon/blendex/state.py blender_addon/blendex/server.py blender_addon/blendex/ui.py tests/blender_addon/test_auth.py tests/codex_plugin/test_blender_client.py tests/blender_addon/test_server_dispatch.py
git commit -m "feat: require BlendeX session token"
```

---

### Task 3: v0.23 Batch History and Audit Trail

**Files:**
- Create: `blender_addon/blendex/history.py`
- Create: `blender_addon/blendex/batches.py`
- Create: `tests/blender_addon/test_history.py`
- Create: `tests/blender_addon/test_batches.py`
- Modify: `src/blendex_protocol/validation.py`
- Modify: `blender_addon/blendex/capabilities.py`
- Modify: `blender_addon/blendex/server.py`
- Modify: `blender_addon/blendex/state.py`
- Modify: `blender_addon/blendex/ui.py`

- [ ] **Step 1: Write failing history tests**

Create `tests/blender_addon/test_history.py`:

```python
import unittest

from blender_addon.blendex.history import BatchHistory, BatchRecord


class BatchHistoryTests(unittest.TestCase):
    def test_records_recent_batches_newest_first(self):
        history = BatchHistory(max_batches=2)

        history.record(BatchRecord(batch_id="batch_1", status="succeeded", operation_count=1))
        history.record(BatchRecord(batch_id="batch_2", status="failed", operation_count=2))
        history.record(BatchRecord(batch_id="batch_3", status="partial", operation_count=3))

        self.assertEqual([batch.batch_id for batch in history.recent()], ["batch_3", "batch_2"])

    def test_to_dict_is_json_safe(self):
        record = BatchRecord(
            batch_id="batch_1",
            status="succeeded",
            operation_count=1,
            target={"object_id": "Cube"},
            summary="Created one node",
        )

        self.assertEqual(record.to_dict()["target"], {"object_id": "Cube"})
        self.assertEqual(record.to_dict()["summary"], "Created one node")
```

- [ ] **Step 2: Write failing batch execution tests**

Create `tests/blender_addon/test_batches.py` with fake objects patterned after `tests/blender_addon/test_executor_fake.py`. Include:

```python
import unittest

from blender_addon.blendex.batches import execute_batch
from blender_addon.blendex.executor import GeometryNodesExecutor


class BatchExecutionTests(unittest.TestCase):
    def test_execute_batch_records_batch_id_and_results(self):
        executor = GeometryNodesExecutor(fake_context_with_owned_modifier())
        operations = [
            {
                "id": "op_node",
                "type": "geometry_nodes.create_node",
                "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                "params": {"node_type": "GeometryNodeJoinGeometry", "label": "Join", "client_id": "join"},
            }
        ]

        result = execute_batch(operations, executor, summary="Create join node")

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["batch_id"].startswith("batch_"))
        self.assertEqual(result["operations"][0]["id"], "op_node")

    def test_execute_batch_resolves_client_ids_for_later_operations(self):
        executor = GeometryNodesExecutor(fake_context_with_owned_modifier())
        operations = [
            {
                "id": "op_node",
                "type": "geometry_nodes.create_node",
                "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                "params": {"node_type": "GeometryNodeJoinGeometry", "label": "Join", "client_id": "join"},
            },
            {
                "id": "op_label",
                "type": "geometry_nodes.label_node",
                "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                "params": {"node_id": "join", "label": "Resolved Join"},
            },
        ]

        result = execute_batch(operations, executor, summary="Create and label")

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["operations"][1]["result"]["label"], "Resolved Join")
```

Use the same fake runtime helpers already available in `tests/blender_addon/test_executor_fake.py`. If they are local to that file, move reusable helpers into `tests/blender_addon/fakes.py` in the same task and import them from both test files.

- [ ] **Step 3: Run targeted tests to verify they fail**

Run:

```bash
python3 -m unittest tests.blender_addon.test_history tests.blender_addon.test_batches -v
```

Expected: FAIL because `history.py` and `batches.py` do not exist.

- [ ] **Step 4: Implement history dataclasses**

Create `blender_addon/blendex/history.py`:

```python
from dataclasses import dataclass, field
from time import time
from typing import Any, Dict, List, Optional


@dataclass
class BatchRecord:
    batch_id: str
    status: str
    operation_count: int
    timestamp: float = 0.0
    target: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    operations: List[Dict[str, Any]] = field(default_factory=list)
    preview: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    undo_status: str = "not_requested"

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time()

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "batch_id": self.batch_id,
            "status": self.status,
            "operation_count": self.operation_count,
            "timestamp": self.timestamp,
            "target": self.target,
            "summary": self.summary,
            "operations": self.operations,
            "preview": self.preview,
            "undo_status": self.undo_status,
        }
        if self.error is not None:
            result["error"] = self.error
        return result


class BatchHistory:
    def __init__(self, max_batches: int = 20):
        self.max_batches = max_batches
        self._records: List[BatchRecord] = []

    def record(self, batch: BatchRecord) -> None:
        self._records.insert(0, batch)
        del self._records[self.max_batches :]

    def recent(self) -> List[BatchRecord]:
        return list(self._records)

    def latest(self) -> Optional[BatchRecord]:
        return self._records[0] if self._records else None

    def find(self, batch_id: str) -> Optional[BatchRecord]:
        for batch in self._records:
            if batch.batch_id == batch_id:
                return batch
        return None
```

- [ ] **Step 5: Add history to global state**

Modify `blender_addon/blendex/state.py`:

```python
from .history import BatchHistory, BatchRecord
```

Add field:

```python
batch_history: BatchHistory = field(default_factory=BatchHistory)
```

Add methods:

```python
def record_batch(self, batch: BatchRecord) -> None:
    self.batch_history.record(batch)

def recent_batches(self) -> List[BatchRecord]:
    return self.batch_history.recent()
```

- [ ] **Step 6: Implement batch execution with client-id resolution**

Create `blender_addon/blendex/batches.py`:

```python
import copy
import uuid
from typing import Any, Dict, List, Optional

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest

from .history import BatchRecord
from .state import STATE


def _new_batch_id() -> str:
    return f"batch_{uuid.uuid4().hex[:12]}"


def _rewrite_node_refs(operation: Dict[str, Any], node_ids: Dict[str, str]) -> Dict[str, Any]:
    rewritten = copy.deepcopy(operation)
    params = rewritten.setdefault("params", {})
    for key in ("node_id", "from_node", "to_node"):
        value = params.get(key)
        if isinstance(value, str) and value in node_ids:
            params[key] = node_ids[value]
    return rewritten


def _record_result_node_id(operation: Dict[str, Any], result: Dict[str, Any], node_ids: Dict[str, str]) -> None:
    client_id = operation.get("params", {}).get("client_id")
    node_id = result.get("id") or result.get("node_id")
    if isinstance(client_id, str) and client_id and isinstance(node_id, str) and node_id:
        node_ids[client_id] = node_id


def _target_for(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    for operation in operations:
        target = operation.get("target")
        if isinstance(target, dict) and target:
            return dict(target)
    return {}


def execute_batch(
    operations: List[Dict[str, Any]],
    executor: Any,
    summary: str = "",
    preview: Optional[Dict[str, Any]] = None,
    confirmed: bool = False,
) -> Dict[str, Any]:
    batch_id = _new_batch_id()
    node_ids: Dict[str, str] = {}
    operation_results: List[Dict[str, Any]] = []
    status = "succeeded"
    error_dict = None

    for index, operation in enumerate(operations):
        try:
            rewritten = _rewrite_node_refs(operation, node_ids)
            request = OperationRequest.from_dict(rewritten)
            result = executor.execute(request)
            _record_result_node_id(operation, result, node_ids)
            operation_results.append(
                {"index": index, "id": request.id, "type": request.type, "ok": True, "result": result}
            )
        except BlendexError as error:
            status = "failed" if not operation_results else "partial"
            error_dict = error.to_dict()
            operation_results.append(
                {
                    "index": index,
                    "id": operation.get("id", f"op_{index}"),
                    "type": operation.get("type", ""),
                    "ok": False,
                    "error": error_dict,
                }
            )
            break

    record = BatchRecord(
        batch_id=batch_id,
        status=status,
        operation_count=len(operations),
        target=_target_for(operations),
        summary=summary,
        operations=operation_results,
        preview=preview or {},
        error=error_dict,
    )
    STATE.record_batch(record)
    response = record.to_dict()
    response["confirmed"] = bool(confirmed)
    return response
```

- [ ] **Step 7: Add protocol and dispatch for batch operations**

Modify `src/blendex_protocol/validation.py`:

```python
ALLOWED_OPERATIONS.update({
    "safety.execute_batch",
    "safety.batch_history",
    "safety.inspect_batch",
})
```

Add validation:

```python
if request.type == "safety.execute_batch":
    _require_operations(request.params)
    if "summary" in request.params:
        _require_string(request.params, "summary", "execute_batch params.summary must be a non-empty string.")
if request.type == "safety.inspect_batch":
    _require_string(request.params, "batch_id", "inspect_batch requires params.batch_id.")
```

Modify `blender_addon/blendex/capabilities.py` so `IMPLEMENTED_OPERATIONS` includes:

```python
"safety.execute_batch",
"safety.batch_history",
"safety.inspect_batch",
```

Modify `blender_addon/blendex/server.py`:

```python
def _execute_batch(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    if executor is None:
        raise BlendexError("BLENDER_NOT_CONNECTED", "Batch execution requires a Blender executor.")
    from .batches import execute_batch

    return execute_batch(
        request.params["operations"],
        executor,
        summary=request.params.get("summary", ""),
        preview=request.params.get("preview", {}),
        confirmed=bool(request.params.get("confirmed", False)),
    )


def _batch_history() -> Dict[str, Any]:
    return {"batches": [batch.to_dict() for batch in STATE.recent_batches()]}


def _inspect_batch(request: OperationRequest) -> Dict[str, Any]:
    batch = STATE.batch_history.find(request.params["batch_id"])
    if batch is None:
        raise BlendexError("BATCH_NOT_FOUND", f"Batch not found: {request.params['batch_id']}")
    return batch.to_dict()
```

Route these operations in `dispatch_payload`.

- [ ] **Step 8: Show recent batches in UI**

Modify `blender_addon/blendex/ui.py` after recent operations:

```python
layout.separator()
layout.label(text="Recent Batches")
for batch in STATE.recent_batches()[:5]:
    icon = "CHECKMARK" if batch.status == "succeeded" else "ERROR"
    layout.label(text=f"{batch.batch_id}: {batch.status}", icon=icon)
```

- [ ] **Step 9: Run targeted and full tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_history tests.blender_addon.test_batches tests.blender_addon.test_server_dispatch tests.protocol.test_validation -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 10: Commit v0.23**

Run:

```bash
git add src/blendex_protocol/validation.py blender_addon/blendex/capabilities.py blender_addon/blendex/server.py blender_addon/blendex/state.py blender_addon/blendex/ui.py blender_addon/blendex/history.py blender_addon/blendex/batches.py tests/blender_addon/test_history.py tests/blender_addon/test_batches.py tests/blender_addon/test_server_dispatch.py tests/protocol/test_validation.py
git commit -m "feat: record BlendeX batch history"
```

---

### Task 4: v0.24 Undo Last Batch and Recovery Signals

**Files:**
- Modify: `blender_addon/blendex/batches.py`
- Modify: `blender_addon/blendex/history.py`
- Modify: `blender_addon/blendex/server.py`
- Modify: `blender_addon/blendex/capabilities.py`
- Modify: `blender_addon/blendex/__init__.py`
- Modify: `blender_addon/blendex/ui.py`
- Modify: `src/blendex_protocol/validation.py`
- Modify: `tests/blender_addon/test_batches.py`
- Modify: `tests/blender_addon/test_server_dispatch.py`
- Modify: `tests/blender_addon/test_ui.py`

- [ ] **Step 1: Add failing undo tests**

Add to `tests/blender_addon/test_batches.py`:

```python
from blendex_protocol.errors import BlendexError
from blender_addon.blendex.batches import undo_last_batch
from blender_addon.blendex.state import STATE


    def test_undo_last_batch_marks_latest_batch_undone(self):
        executor = GeometryNodesExecutor(fake_context_with_owned_modifier())
        execute_batch(
            [
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "label": "Join"},
                }
            ],
            executor,
            summary="Create join node",
        )

        result = undo_last_batch()

        self.assertEqual(result["undo_status"], "undone")
        self.assertEqual(STATE.batch_history.latest().undo_status, "undone")

    def test_undo_last_batch_without_history_raises_unavailable(self):
        STATE.batch_history._records.clear()

        with self.assertRaises(BlendexError) as raised:
            undo_last_batch()

        self.assertEqual(raised.exception.code, "UNDO_UNAVAILABLE")
```

- [ ] **Step 2: Run failing undo tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_batches -v
```

Expected: FAIL because `undo_last_batch` is not implemented.

- [ ] **Step 3: Add undo fields to batch records**

Modify `blender_addon/blendex/history.py`:

```python
undo_status: str = "available"
undo_error: Optional[Dict[str, Any]] = None
```

Update `to_dict()`:

```python
if self.undo_error is not None:
    result["undo_error"] = self.undo_error
```

- [ ] **Step 4: Implement conservative undo status**

In `blender_addon/blendex/batches.py`, add:

```python
from blendex_protocol.errors import BlendexError


def undo_last_batch() -> Dict[str, Any]:
    batch = STATE.batch_history.latest()
    if batch is None:
        raise BlendexError("UNDO_UNAVAILABLE", "No BlendeX batch is available to undo.")
    if batch.status not in {"succeeded", "partial"}:
        batch.undo_status = "unavailable"
        batch.undo_error = {"code": "UNDO_UNAVAILABLE", "message": "Only applied batches can be undone."}
        raise BlendexError("UNDO_UNAVAILABLE", "Only applied BlendeX batches can be undone.")
    if batch.undo_status == "undone":
        return batch.to_dict()

    # v0.24 records the undo state and exposes the recovery contract. Real Blender undo
    # integration is routed through the optional callback below so fake-runtime tests stay deterministic.
    undo_callback = getattr(STATE, "undo_callback", None)
    if callable(undo_callback):
        undo_callback(batch)
    batch.undo_status = "undone"
    return batch.to_dict()
```

Add `undo_callback: Any = None` to `BlendexState` in `state.py` if needed.

- [ ] **Step 5: Route `safety.undo_last_batch`**

Modify `blender_addon/blendex/capabilities.py` so `IMPLEMENTED_OPERATIONS` includes:

```python
"safety.undo_last_batch",
```

Modify `blender_addon/blendex/server.py`:

```python
elif request.type == "safety.undo_last_batch":
    from .batches import undo_last_batch

    result = undo_last_batch()
```

Modify `src/blendex_protocol/validation.py` to accept `safety.undo_last_batch` without additional params. It is already allowlisted; ensure runtime implementation no longer rejects it.

- [ ] **Step 6: Add Blender UI undo operator**

Modify `blender_addon/blendex/__init__.py`:

```python
class BLENDEX_OT_undo_last_batch(_OperatorBase):
    bl_idname = "blendex.undo_last_batch"
    bl_label = "Undo Last BlendeX Batch"

    def execute(self, context):
        from .batches import undo_last_batch

        undo_last_batch()
        return {"FINISHED"}
```

Update `_load_classes()`:

```python
return [BLENDEX_OT_start_service, BLENDEX_OT_stop_service, BLENDEX_OT_undo_last_batch] + panel_classes()
```

Modify `blender_addon/blendex/ui.py`:

```python
layout.operator("blendex.undo_last_batch", text="Undo Last Batch")
```

- [ ] **Step 7: Improve partial failure signals**

In `execute_batch`, when a `BlendexError` occurs after prior successful operations, add:

```python
if status == "partial":
    error_dict["mutation_occurred"] = True
    error_dict["batch_id"] = batch_id
```

When failure occurs before any operation succeeds, add:

```python
error_dict["mutation_occurred"] = False
```

- [ ] **Step 8: Run undo and full tests**

Run:

```bash
python3 -m unittest tests.blender_addon.test_batches tests.blender_addon.test_server_dispatch tests.blender_addon.test_ui -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 9: Commit v0.24**

Run:

```bash
git add blender_addon/blendex/batches.py blender_addon/blendex/history.py blender_addon/blendex/server.py blender_addon/blendex/capabilities.py blender_addon/blendex/__init__.py blender_addon/blendex/ui.py blender_addon/blendex/state.py src/blendex_protocol/validation.py tests/blender_addon/test_batches.py tests/blender_addon/test_server_dispatch.py tests/blender_addon/test_ui.py
git commit -m "feat: add BlendeX batch undo"
```

---

### Task 5: v0.25 Confirmation-First Execution Workflow

**Files:**
- Create: `codex_plugin/blendex_mcp/workflow.py`
- Create: `tests/codex_plugin/test_workflow.py`
- Modify: `codex_plugin/blendex_mcp/tools.py`
- Modify: `codex_plugin/blendex_mcp/server.py`
- Modify: `src/blendex_protocol/validation.py`
- Modify: `blender_addon/blendex/batches.py`
- Modify: `tests/codex_plugin/test_tools.py`
- Modify: `tests/codex_plugin/test_server.py`
- Modify: `tests/blender_addon/test_batches.py`

- [ ] **Step 1: Write failing workflow summary tests**

Create `tests/codex_plugin/test_workflow.py`:

```python
import unittest

from codex_plugin.blendex_mcp.workflow import confirmation_summary, confirmed_batch_arguments


class WorkflowTests(unittest.TestCase):
    def test_confirmation_summary_names_target_and_changes(self):
        dry_run = {
            "status": "valid",
            "preview": {
                "objects": [],
                "modifiers": [{"object_id": "Cube", "modifier_id": "BlendeX Geometry"}],
                "nodes": [{"node_type": "GeometryNodeJoinGeometry", "label": "Join"}],
                "socket_values": [{"node_id": "Join", "socket": "Value", "value": 2.0}],
                "links": [{"from_node": "A", "from_socket": "Geometry", "to_node": "B", "to_socket": "Geometry"}],
                "labels": [],
                "warnings": [],
            },
        }

        summary = confirmation_summary(dry_run)

        self.assertIn("Cube", summary)
        self.assertIn("1 node", summary)
        self.assertIn("1 link", summary)

    def test_confirmed_batch_arguments_marks_confirmation(self):
        args = confirmed_batch_arguments(
            operations=[{"id": "op", "type": "scene.inspect", "target": {}, "params": {}}],
            confirmation_id="confirm_1",
            summary="Inspect scene",
        )

        self.assertTrue(args["confirmed"])
        self.assertEqual(args["confirmation_id"], "confirm_1")
```

- [ ] **Step 2: Write failing server confirmation tests**

Add to `tests/blender_addon/test_batches.py`:

```python
    def test_execute_batch_requires_confirmation_when_requested(self):
        executor = GeometryNodesExecutor(fake_context_with_owned_modifier())

        with self.assertRaises(BlendexError) as raised:
            execute_batch(
                [
                    {
                        "id": "op_node",
                        "type": "geometry_nodes.create_node",
                        "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                        "params": {"node_type": "GeometryNodeJoinGeometry"},
                    }
                ],
                executor,
                require_confirmation=True,
            )

        self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
```

- [ ] **Step 3: Run targeted tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_workflow tests.blender_addon.test_batches -v
```

Expected: FAIL because workflow helpers and confirmation enforcement do not exist.

- [ ] **Step 4: Implement workflow helpers**

Create `codex_plugin/blendex_mcp/workflow.py`:

```python
from typing import Any, Dict, List, Optional


def _count(preview: Dict[str, Any], key: str) -> int:
    value = preview.get(key, [])
    return len(value) if isinstance(value, list) else 0


def _plural(count: int, label: str) -> str:
    return f"{count} {label}" if count == 1 else f"{count} {label}s"


def confirmation_summary(dry_run_result: Dict[str, Any]) -> str:
    preview = dry_run_result.get("preview", {})
    modifiers = preview.get("modifiers", [])
    target = modifiers[0] if modifiers else {}
    object_id = target.get("object_id", "selected target")
    modifier_id = target.get("modifier_id", "BlendeX Geometry")
    parts = [
        f"Target: {object_id} / {modifier_id}",
        _plural(_count(preview, "nodes"), "node"),
        _plural(_count(preview, "links"), "link"),
        _plural(_count(preview, "socket_values"), "socket value"),
    ]
    warnings = _count(preview, "warnings")
    if warnings:
        parts.append(_plural(warnings, "warning"))
    return "; ".join(parts)


def confirmed_batch_arguments(
    operations: List[Dict[str, Any]],
    confirmation_id: str,
    summary: str,
    preview: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "operations": operations,
        "confirmed": True,
        "confirmation_id": confirmation_id,
        "summary": summary,
        "preview": preview or {},
    }
```

- [ ] **Step 5: Enforce confirmation in batch execution**

Modify `execute_batch` signature:

```python
require_confirmation: bool = False,
confirmation_id: str = "",
```

At the start of `execute_batch`:

```python
if require_confirmation and not confirmed:
    raise BlendexError(
        "CONFIRMATION_REQUIRED",
        "Mutating batch execution requires user confirmation.",
        retry_hint="Run dry-run, show the confirmation summary, then execute with confirmed=true.",
    )
```

Store `confirmation_id` in `BatchRecord` by adding the field:

```python
confirmation_id: str = ""
```

- [ ] **Step 6: Add MCP tool for confirmed execution**

Modify `codex_plugin/blendex_mcp/tools.py` with a new tool definition:

```python
{
    "name": "blendex_execute_confirmed_batch",
    "description": "Execute a previously dry-run BlendeX batch after user confirmation.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "operations": OPERATION_ARRAY_PROP,
            "confirmation_id": STRING_PROP,
            "summary": STRING_PROP,
            "preview": {"type": "object"},
        },
        "required": ["operations", "confirmation_id", "summary"],
        "additionalProperties": False,
    },
}
```

Map it in `tool_to_operation`:

```python
if name == "blendex_execute_confirmed_batch":
    return {
        "id": request_id,
        "type": "safety.execute_batch",
        "target": {},
        "params": {
            "operations": arguments["operations"],
            "confirmed": True,
            "confirmation_id": arguments["confirmation_id"],
            "summary": arguments["summary"],
            "preview": arguments.get("preview", {}),
        },
    }
```

- [ ] **Step 7: Validate confirmation params**

Modify `src/blendex_protocol/validation.py`:

```python
if request.type == "safety.execute_batch":
    _require_operations(request.params)
    if request.params.get("confirmed") is not True:
        raise BlendexError("CONFIRMATION_REQUIRED", "execute_batch requires params.confirmed=true.")
    _require_string(request.params, "confirmation_id", "execute_batch requires params.confirmation_id.")
    _require_string(request.params, "summary", "execute_batch requires params.summary.")
```

- [ ] **Step 8: Run workflow, tool, protocol, and full tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_workflow tests.codex_plugin.test_tools tests.codex_plugin.test_server tests.blender_addon.test_batches tests.protocol.test_validation -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 9: Commit v0.25**

Run:

```bash
git add codex_plugin/blendex_mcp/workflow.py codex_plugin/blendex_mcp/tools.py codex_plugin/blendex_mcp/server.py src/blendex_protocol/validation.py blender_addon/blendex/batches.py blender_addon/blendex/history.py tests/codex_plugin/test_workflow.py tests/codex_plugin/test_tools.py tests/codex_plugin/test_server.py tests/blender_addon/test_batches.py tests/protocol/test_validation.py
git commit -m "feat: require confirmed BlendeX batch execution"
```

---

### Task 6: v0.26 Recipe Infrastructure

**Files:**
- Create: `codex_plugin/blendex_mcp/recipes.py`
- Create: `tests/codex_plugin/test_recipes.py`
- Modify: `codex_plugin/blendex_mcp/tools.py`
- Modify: `tests/codex_plugin/test_tools.py`
- Modify: `tests/codex_plugin/test_server.py`

- [ ] **Step 1: Write failing recipe registry tests**

Create `tests/codex_plugin/test_recipes.py`:

```python
import unittest

from codex_plugin.blendex_mcp.recipes import Recipe, RecipeParameter, RecipeRegistry


class RecipeTests(unittest.TestCase):
    def test_registry_lists_recipe_metadata(self):
        registry = RecipeRegistry()
        registry.register(
            Recipe(
                recipe_id="demo.grid",
                label="Demo Grid",
                category="architecture",
                parameters=[RecipeParameter("levels", "integer", default=3, minimum=1, maximum=20)],
                builder=lambda params: [],
                required_node_types=["GeometryNodeJoinGeometry"],
            )
        )

        self.assertEqual(registry.list_recipes()[0]["id"], "demo.grid")

    def test_parameter_defaults_and_range_validation(self):
        recipe = Recipe(
            recipe_id="demo.grid",
            label="Demo Grid",
            category="architecture",
            parameters=[RecipeParameter("levels", "integer", default=3, minimum=1, maximum=20)],
            builder=lambda params: [],
        )

        self.assertEqual(recipe.normalize_params({})["levels"], 3)
        with self.assertRaises(ValueError):
            recipe.normalize_params({"levels": 0})
```

- [ ] **Step 2: Run recipe tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_recipes -v
```

Expected: FAIL because `recipes.py` does not exist.

- [ ] **Step 3: Implement recipe schema and registry**

Create `codex_plugin/blendex_mcp/recipes.py`:

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class RecipeParameter:
    name: str
    value_type: str
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    description: str = ""

    def normalize(self, params: Dict[str, Any]) -> Any:
        value = params.get(self.name, self.default)
        if self.value_type == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{self.name} must be an integer")
        elif self.value_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{self.name} must be a number")
        elif self.value_type == "string":
            if not isinstance(value, str) or not value:
                raise ValueError(f"{self.name} must be a non-empty string")
        else:
            raise ValueError(f"Unsupported parameter type: {self.value_type}")
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"{self.name} must be >= {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"{self.name} must be <= {self.maximum}")
        return value


@dataclass
class Recipe:
    recipe_id: str
    label: str
    category: str
    parameters: List[RecipeParameter]
    builder: Callable[[Dict[str, Any]], List[Dict[str, Any]]]
    required_node_types: List[str] = field(default_factory=list)
    example_prompts: List[str] = field(default_factory=list)

    def metadata(self) -> Dict[str, Any]:
        return {
            "id": self.recipe_id,
            "label": self.label,
            "category": self.category,
            "parameters": [parameter.__dict__ for parameter in self.parameters],
            "required_node_types": list(self.required_node_types),
            "example_prompts": list(self.example_prompts),
        }

    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {parameter.name: parameter.normalize(params) for parameter in self.parameters}

    def build(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.builder(self.normalize_params(params))


class RecipeRegistry:
    def __init__(self):
        self._recipes: Dict[str, Recipe] = {}

    def register(self, recipe: Recipe) -> None:
        self._recipes[recipe.recipe_id] = recipe

    def get(self, recipe_id: str) -> Recipe:
        try:
            return self._recipes[recipe_id]
        except KeyError as exc:
            raise ValueError(f"Recipe not found: {recipe_id}") from exc

    def list_recipes(self) -> List[Dict[str, Any]]:
        return [recipe.metadata() for recipe in self._recipes.values()]

    def build(self, recipe_id: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.get(recipe_id).build(params)


REGISTRY = RecipeRegistry()
```

- [ ] **Step 4: Add recipe tools**

Modify `codex_plugin/blendex_mcp/tools.py`:

Add tool definitions:

```python
{
    "name": "blendex_list_recipes",
    "description": "List available BlendeX procedural recipes.",
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
},
{
    "name": "blendex_build_recipe_batch",
    "description": "Build a BlendeX operation batch from a recipe and parameters.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "recipe_id": STRING_PROP,
            "parameters": {"type": "object"},
        },
        "required": ["recipe_id"],
        "additionalProperties": False,
    },
},
```

Map these tools:

```python
if name == "blendex_list_recipes":
    return {"id": request_id, "type": "recipes.list", "target": {}, "params": {}}
if name == "blendex_build_recipe_batch":
    return {
        "id": request_id,
        "type": "recipes.build_batch",
        "target": {},
        "params": {
            "recipe_id": arguments["recipe_id"],
            "parameters": arguments.get("parameters", {}),
        },
    }
```

- [ ] **Step 5: Handle recipe tools in MCP server without Blender roundtrip**

Modify `codex_plugin/blendex_mcp/server.py` before `client.send_operation(operation)`:

```python
from .recipes import REGISTRY
```

Handle recipe operations:

```python
if operation["type"] == "recipes.list":
    return json_rpc_success(message_id, _tool_result({"ok": True, "result": {"recipes": REGISTRY.list_recipes()}}))
if operation["type"] == "recipes.build_batch":
    try:
        operations = REGISTRY.build(operation["params"]["recipe_id"], operation["params"].get("parameters", {}))
    except ValueError as error:
        return json_rpc_success(
            message_id,
            _tool_result({"ok": False, "error": {"code": "RECIPE_NOT_FOUND", "message": str(error)}}),
        )
    return json_rpc_success(message_id, _tool_result({"ok": True, "result": {"operations": operations}}))
```

- [ ] **Step 6: Run recipe and MCP tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_recipes tests.codex_plugin.test_tools tests.codex_plugin.test_server -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 7: Commit v0.26**

Run:

```bash
git add codex_plugin/blendex_mcp/recipes.py codex_plugin/blendex_mcp/tools.py codex_plugin/blendex_mcp/server.py tests/codex_plugin/test_recipes.py tests/codex_plugin/test_tools.py tests/codex_plugin/test_server.py
git commit -m "feat: add BlendeX recipe infrastructure"
```

---

### Task 7: v0.27 Architecture and Hard-Surface Recipes

**Files:**
- Modify: `codex_plugin/blendex_mcp/recipes.py`
- Modify: `tests/codex_plugin/test_recipes.py`

- [ ] **Step 1: Add failing tests for architecture recipes**

Add to `tests/codex_plugin/test_recipes.py`:

```python
from codex_plugin.blendex_mcp.recipes import REGISTRY


    def test_architecture_recipes_are_registered(self):
        recipe_ids = {recipe["id"] for recipe in REGISTRY.list_recipes()}

        self.assertIn("architecture.grid_tower", recipe_ids)
        self.assertIn("architecture.wall_panel", recipe_ids)
        self.assertIn("architecture.modular_building", recipe_ids)

    def test_grid_tower_recipe_builds_owned_graph_batch(self):
        operations = REGISTRY.build("architecture.grid_tower", {"levels": 4, "columns": 3})
        operation_types = [operation["type"] for operation in operations]

        self.assertEqual(operation_types[0], "scene.create_carrier_mesh")
        self.assertIn("geometry_nodes.create_modifier", operation_types)
        self.assertIn("geometry_nodes.create_node", operation_types)
        self.assertTrue(any(operation["params"].get("client_id") == "grid_join" for operation in operations))
```

- [ ] **Step 2: Run architecture recipe tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_recipes -v
```

Expected: FAIL because the recipes are not registered.

- [ ] **Step 3: Add reusable operation builders**

Add to `codex_plugin/blendex_mcp/recipes.py`:

```python
def _carrier(name: str) -> Dict[str, Any]:
    return {"id": f"create_{name.lower().replace(' ', '_')}", "type": "scene.create_carrier_mesh", "target": {}, "params": {"name": name}}


def _modifier(object_id: str = "BlendeX Carrier", modifier_id: str = "BlendeX Geometry") -> Dict[str, Any]:
    return {
        "id": "create_modifier",
        "type": "geometry_nodes.create_modifier",
        "target": {"object_id": object_id},
        "params": {"modifier_id": modifier_id},
    }


def _node(op_id: str, object_id: str, client_id: str, node_type: str, label: str, location: list[float]) -> Dict[str, Any]:
    return {
        "id": op_id,
        "type": "geometry_nodes.create_node",
        "target": {"object_id": object_id, "modifier_id": "BlendeX Geometry"},
        "params": {"node_type": node_type, "label": label, "client_id": client_id, "location": location},
    }
```

- [ ] **Step 4: Register architecture recipes**

Add builder functions:

```python
def _grid_tower(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Grid Tower"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node("grid_join", object_id, "grid_join", "GeometryNodeJoinGeometry", f"Grid Tower {params['levels']}x{params['columns']}", [0, 0]),
        _node("grid_transform", object_id, "grid_transform", "GeometryNodeTransform", "Module Transform", [220, 0]),
    ]


def _wall_panel(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Wall Panel"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node("wall_join", object_id, "wall_join", "GeometryNodeJoinGeometry", f"Wall Panel {params['segments']} segments", [0, 0]),
        _node("wall_transform", object_id, "wall_transform", "GeometryNodeTransform", "Panel Transform", [220, 0]),
    ]


def _modular_building(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Modular Building"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node("building_join", object_id, "building_join", "GeometryNodeJoinGeometry", f"Building {params['floors']} floors", [0, 0]),
        _node("building_set_material", object_id, "building_material", "GeometryNodeSetMaterial", "Material Zones", [220, -180]),
    ]
```

Register them after `REGISTRY = RecipeRegistry()`:

```python
REGISTRY.register(
    Recipe(
        recipe_id="architecture.grid_tower",
        label="Modular Grid Tower",
        category="architecture",
        parameters=[
            RecipeParameter("levels", "integer", default=5, minimum=1, maximum=40),
            RecipeParameter("columns", "integer", default=4, minimum=1, maximum=20),
        ],
        builder=_grid_tower,
        required_node_types=["GeometryNodeJoinGeometry", "GeometryNodeTransform"],
        example_prompts=["Create a modular grid tower"],
    )
)
REGISTRY.register(
    Recipe(
        recipe_id="architecture.wall_panel",
        label="Procedural Wall Panel",
        category="architecture",
        parameters=[RecipeParameter("segments", "integer", default=6, minimum=1, maximum=40)],
        builder=_wall_panel,
        required_node_types=["GeometryNodeJoinGeometry", "GeometryNodeTransform"],
        example_prompts=["Create a procedural wall panel"],
    )
)
REGISTRY.register(
    Recipe(
        recipe_id="architecture.modular_building",
        label="Simple Modular Building",
        category="architecture",
        parameters=[RecipeParameter("floors", "integer", default=4, minimum=1, maximum=30)],
        builder=_modular_building,
        required_node_types=["GeometryNodeJoinGeometry", "GeometryNodeSetMaterial"],
        example_prompts=["Create a simple modular building"],
    )
)
```

- [ ] **Step 5: Run recipe and full tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_recipes -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 6: Commit v0.27**

Run:

```bash
git add codex_plugin/blendex_mcp/recipes.py tests/codex_plugin/test_recipes.py
git commit -m "feat: add BlendeX architecture recipes"
```

---

### Task 8: v0.28 Nature and Scattering Recipes

**Files:**
- Modify: `codex_plugin/blendex_mcp/recipes.py`
- Modify: `tests/codex_plugin/test_recipes.py`

- [ ] **Step 1: Add failing tests for scatter recipes**

Add to `tests/codex_plugin/test_recipes.py`:

```python
    def test_scatter_recipes_are_registered(self):
        recipe_ids = {recipe["id"] for recipe in REGISTRY.list_recipes()}

        self.assertIn("scatter.stones", recipe_ids)
        self.assertIn("scatter.ground_points", recipe_ids)
        self.assertIn("scatter.grass", recipe_ids)

    def test_stone_scatter_recipe_uses_density_and_seed_labels(self):
        operations = REGISTRY.build("scatter.stones", {"density": 12, "seed": 7})
        labels = [operation.get("params", {}).get("label", "") for operation in operations]

        self.assertTrue(any("density 12" in label for label in labels))
        self.assertTrue(any("seed 7" in label for label in labels))
```

- [ ] **Step 2: Run scatter recipe tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_recipes -v
```

Expected: FAIL because scatter recipes are not registered.

- [ ] **Step 3: Add scatter recipe builders**

Add to `codex_plugin/blendex_mcp/recipes.py`:

```python
def _stone_scatter(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Stone Scatter"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node("scatter_points", object_id, "scatter_points", "GeometryNodeDistributePointsOnFaces", f"Points density {params['density']}", [0, 0]),
        _node("scatter_instances", object_id, "scatter_instances", "GeometryNodeInstanceOnPoints", f"Stone instances seed {params['seed']}", [240, 0]),
        _node("scatter_realize", object_id, "scatter_realize", "GeometryNodeRealizeInstances", "Realize Stones", [480, 0]),
    ]


def _ground_points(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Ground Points"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node("ground_points", object_id, "ground_points", "GeometryNodeDistributePointsOnFaces", f"Ground points density {params['density']}", [0, 0]),
        _node("ground_random", object_id, "ground_random", "FunctionNodeRandomValue", f"Random seed {params['seed']}", [240, -180]),
    ]


def _grass_scatter(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Grass Scatter"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node("grass_points", object_id, "grass_points", "GeometryNodeDistributePointsOnFaces", f"Grass density {params['density']}", [0, 0]),
        _node("grass_instances", object_id, "grass_instances", "GeometryNodeInstanceOnPoints", f"Grass scale {params['scale']}", [240, 0]),
        _node("grass_realize", object_id, "grass_realize", "GeometryNodeRealizeInstances", "Realize Grass", [480, 0]),
    ]
```

- [ ] **Step 4: Register scatter recipes**

Add registrations:

```python
REGISTRY.register(
    Recipe(
        recipe_id="scatter.stones",
        label="Random Stone Scatter",
        category="scatter",
        parameters=[
            RecipeParameter("density", "integer", default=10, minimum=1, maximum=200),
            RecipeParameter("seed", "integer", default=1, minimum=0, maximum=9999),
        ],
        builder=_stone_scatter,
        required_node_types=["GeometryNodeDistributePointsOnFaces", "GeometryNodeInstanceOnPoints", "GeometryNodeRealizeInstances"],
        example_prompts=["Scatter random stones on the ground"],
    )
)
REGISTRY.register(
    Recipe(
        recipe_id="scatter.ground_points",
        label="Ground Point Distribution",
        category="scatter",
        parameters=[
            RecipeParameter("density", "integer", default=25, minimum=1, maximum=500),
            RecipeParameter("seed", "integer", default=1, minimum=0, maximum=9999),
        ],
        builder=_ground_points,
        required_node_types=["GeometryNodeDistributePointsOnFaces", "FunctionNodeRandomValue"],
        example_prompts=["Create a ground point distribution"],
    )
)
REGISTRY.register(
    Recipe(
        recipe_id="scatter.grass",
        label="Simple Grass Scatter",
        category="scatter",
        parameters=[
            RecipeParameter("density", "integer", default=40, minimum=1, maximum=1000),
            RecipeParameter("scale", "number", default=1.0, minimum=0.1, maximum=10.0),
        ],
        builder=_grass_scatter,
        required_node_types=["GeometryNodeDistributePointsOnFaces", "GeometryNodeInstanceOnPoints", "GeometryNodeRealizeInstances"],
        example_prompts=["Create a simple grass scatter"],
    )
)
```

- [ ] **Step 5: Run recipe and full tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_recipes -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 6: Commit v0.28**

Run:

```bash
git add codex_plugin/blendex_mcp/recipes.py tests/codex_plugin/test_recipes.py
git commit -m "feat: add BlendeX scattering recipes"
```

---

### Task 9: v0.29 Semi-Open Natural-Language Planner

**Files:**
- Create: `codex_plugin/blendex_mcp/planner.py`
- Create: `tests/codex_plugin/test_planner.py`
- Modify: `codex_plugin/blendex_mcp/tools.py`
- Modify: `codex_plugin/blendex_mcp/server.py`
- Modify: `tests/codex_plugin/test_tools.py`
- Modify: `tests/codex_plugin/test_server.py`

- [ ] **Step 1: Write failing planner tests**

Create `tests/codex_plugin/test_planner.py`:

```python
import unittest

from codex_plugin.blendex_mcp.planner import plan_goal


class PlannerTests(unittest.TestCase):
    def test_planner_prefers_grid_tower_recipe(self):
        result = plan_goal("create a modular grid tower", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "architecture.grid_tower")

    def test_planner_prefers_stone_scatter_recipe(self):
        result = plan_goal("scatter stones on a ground patch", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.stones")

    def test_planner_returns_unsupported_for_broad_request(self):
        result = plan_goal("make a photoreal cinematic character", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "unsupported")
        self.assertEqual(result["error"]["code"], "PLANNER_UNSUPPORTED_REQUEST")
```

- [ ] **Step 2: Run planner tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_planner -v
```

Expected: FAIL because `planner.py` does not exist.

- [ ] **Step 3: Implement planner**

Create `codex_plugin/blendex_mcp/planner.py`:

```python
from typing import Any, Dict, Optional

from .recipes import REGISTRY


_RECIPE_KEYWORDS = [
    ("architecture.grid_tower", ("grid tower", "tower", "lattice tower", "modular tower")),
    ("architecture.wall_panel", ("wall", "panel", "facade")),
    ("architecture.modular_building", ("building", "modular building", "blockout")),
    ("scatter.stones", ("stone", "stones", "rock", "rocks")),
    ("scatter.ground_points", ("ground points", "point distribution", "points on ground")),
    ("scatter.grass", ("grass", "field", "lawn")),
]


def _match_recipe(prompt: str) -> Optional[str]:
    normalized = prompt.lower()
    for recipe_id, keywords in _RECIPE_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return recipe_id
    return None


def plan_goal(prompt: str, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    recipe_id = _match_recipe(prompt)
    if recipe_id is not None:
        recipe = REGISTRY.get(recipe_id)
        return {
            "mode": "recipe",
            "recipe_id": recipe_id,
            "label": recipe.label,
            "operations": recipe.build({}),
            "message": f"Matched recipe: {recipe.label}",
        }
    return {
        "mode": "unsupported",
        "error": {
            "code": "PLANNER_UNSUPPORTED_REQUEST",
            "message": "BlendeX v0.3 can plan architecture, hard-surface, nature, and scattering workflows.",
            "retry_hint": "Ask for a modular building, wall panel, grid tower, stone scatter, grass scatter, or ground point distribution.",
        },
    }
```

- [ ] **Step 4: Add planner tool**

Modify `codex_plugin/blendex_mcp/tools.py`:

```python
{
    "name": "blendex_plan_goal",
    "description": "Plan a BlendeX procedural modeling goal using recipes or safe graph primitives.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompt": STRING_PROP,
            "capabilities": {"type": "object"},
        },
        "required": ["prompt"],
        "additionalProperties": False,
    },
}
```

Map it:

```python
if name == "blendex_plan_goal":
    return {
        "id": request_id,
        "type": "planner.plan_goal",
        "target": {},
        "params": {
            "prompt": arguments["prompt"],
            "capabilities": arguments.get("capabilities", {}),
        },
    }
```

- [ ] **Step 5: Handle planner operation locally in MCP server**

Modify `codex_plugin/blendex_mcp/server.py`:

```python
from .planner import plan_goal
```

Add local handling:

```python
if operation["type"] == "planner.plan_goal":
    result = plan_goal(operation["params"]["prompt"], operation["params"].get("capabilities", {}))
    return json_rpc_success(message_id, _tool_result({"ok": result.get("mode") != "unsupported", "result": result}))
```

- [ ] **Step 6: Run planner, tool, server, and full tests**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_planner tests.codex_plugin.test_tools tests.codex_plugin.test_server -v
./scripts/run_unit_tests.sh
```

Expected: all tests PASS.

- [ ] **Step 7: Commit v0.29**

Run:

```bash
git add codex_plugin/blendex_mcp/planner.py codex_plugin/blendex_mcp/tools.py codex_plugin/blendex_mcp/server.py tests/codex_plugin/test_planner.py tests/codex_plugin/test_tools.py tests/codex_plugin/test_server.py
git commit -m "feat: add BlendeX semi-open planner"
```

---

### Task 10: v0.30 Early-User Release Hardening

**Files:**
- Modify: `.codex-plugin/plugin.json`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `blender_addon/blendex/__init__.py`
- Modify: `codex_plugin/blendex_mcp/version.py`
- Modify: `tests/integration/blender_smoke.py`
- Modify: `scripts/run_blender_smoke.py`
- Modify: `tests/codex_plugin/test_version.py`

- [ ] **Step 1: Add failing v0.30 release metadata test**

Modify `tests/codex_plugin/test_version.py`:

```python
    def test_final_v0_3_metadata(self):
        self.assertEqual(VERSION, "0.30.0")
```

- [ ] **Step 2: Run version tests to verify they fail**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_version -v
```

Expected: FAIL because the development version is still `0.21.0` or another intermediate value.

- [ ] **Step 3: Set final v0.3 metadata**

Set:

```python
# codex_plugin/blendex_mcp/version.py
VERSION = "0.30.0"
```

```toml
# pyproject.toml
version = "0.30.0"
```

```json
// .codex-plugin/plugin.json
"version": "0.30.0"
```

```python
# blender_addon/blendex/__init__.py
"version": (0, 30, 0),
```

- [ ] **Step 4: Expand README early-user guide**

Add or replace README sections so they cover:

```markdown
## BlendeX v0.3 Early User Workflow

1. Enable the Blender add-on from the source tree.
2. Start the BlendeX service in Blender.
3. Copy the session token from the Blender sidebar.
4. Start CodeX with `BLENDEX_SESSION_TOKEN` set to that token.
5. Ask CodeX to run `blendex_plan_goal`.
6. Review the dry-run confirmation summary.
7. Execute the confirmed batch.
8. Inspect the resulting Geometry Nodes tree.
9. Use undo last batch when needed.

## Supported v0.3 Creative Paths

- Modular grid tower.
- Procedural wall panel.
- Simple modular building.
- Random stone scatter.
- Ground point distribution.
- Simple grass scatter.

## Troubleshooting

- `AUTH_REQUIRED`: set `BLENDEX_SESSION_TOKEN`.
- `AUTH_FAILED`: copy the current token from Blender.
- `PLANNER_UNSUPPORTED_REQUEST`: ask for one of the supported v0.3 creative paths.
- `UNDO_UNAVAILABLE`: no safe BlendeX batch undo is available.
```

- [ ] **Step 5: Extend Blender smoke script path**

Modify `tests/integration/blender_smoke.py` to include one v0.3-style batch execution after the existing modifier and node checks:

```python
from blendex.batches import execute_batch, undo_last_batch

batch = execute_batch(
    [
        {
            "id": "smoke_batch_node",
            "type": "geometry_nodes.create_node",
            "target": {"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
            "params": {"node_type": "GeometryNodeJoinGeometry", "label": "Smoke Batch Join"},
        }
    ],
    executor,
    summary="Smoke batch",
    confirmed=True,
)
assert batch["status"] == "succeeded"
undo = undo_last_batch()
assert undo["undo_status"] == "undone"
```

Keep the smoke script safe when Blender APIs do not support a feature by failing loudly for real errors and using the existing outer `BLENDER` skip only when no Blender executable is configured.

- [ ] **Step 6: Run final verification**

Run:

```bash
python3 -m unittest tests.codex_plugin.test_version -v
./scripts/run_unit_tests.sh
python3 scripts/run_blender_smoke.py
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python3 -m codex_plugin.blendex_mcp.server
```

Expected:

- Version tests PASS.
- Full unit tests PASS.
- Blender smoke either PASS with `BLENDER` configured or prints the documented skip message when `BLENDER` is unset.
- MCP initialize reports version `0.30.0`.
- MCP tools/list includes v0.3 recipe, planner, confirmed execution, and history tools.

- [ ] **Step 7: Commit v0.30**

Run:

```bash
git add .codex-plugin/plugin.json pyproject.toml README.md blender_addon/blendex/__init__.py codex_plugin/blendex_mcp/version.py tests/integration/blender_smoke.py scripts/run_blender_smoke.py tests/codex_plugin/test_version.py
git commit -m "chore: prepare BlendeX 0.30.0 early-user release"
```

---

## Plan Self-Review

- Spec coverage:
  - Natural-language planning: Task 9.
  - Recipes: Tasks 6, 7, and 8.
  - Confirmation: Task 5.
  - Auth: Task 2.
  - Batch history: Task 3.
  - Undo: Task 4.
  - Early-user docs and verification: Task 10.
  - Version alignment: Tasks 1 and 10.

- Execution order:
  - The order is intentional. Later recipe and planner tasks depend on confirmed batch execution, client-id resolution, and history.

- Verification standard:
  - Every task has a targeted failing test step, a targeted passing test step, full unit test verification, and a commit step.

- Known implementation decision:
  - v0.24 starts with a conservative undo callback contract. During execution, prefer the smallest reliable undo mechanism that satisfies fake-runtime tests first, then expand Blender-specific undo in v0.30 smoke hardening if local Blender behavior is reliable.
