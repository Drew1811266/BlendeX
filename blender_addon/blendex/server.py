import base64
import hashlib
import json
import logging
import queue
import socket
import struct
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest, OperationResponse
from blendex_protocol.validation import validate_request

from .logs import OperationLog
from .state import STATE


_server_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_startup_event = threading.Event()
_startup_error: Optional[BlendexError] = None
_socket_lock = threading.Lock()
_server_socket: Optional[socket.socket] = None
_active_client_socket: Optional[socket.socket] = None
_SOCKET_TIMEOUT_SECONDS = 0.25
_STARTUP_TIMEOUT_SECONDS = 1.0
_SHUTDOWN_JOIN_SECONDS = 1.0
_MAIN_THREAD_DISPATCH_TIMEOUT_SECONDS = 30.0
_LOGGER = logging.getLogger(__name__)
_main_thread_dispatch_queue: "queue.Queue[_MainThreadDispatchTask]" = queue.Queue()
_main_thread_dispatch_enabled = False


class _MainThreadDispatchTask:
    def __init__(self, payload: Any, executor_factory: Callable[[], Any]):
        self.payload = payload
        self.executor_factory = executor_factory
        self.event = threading.Event()
        self.response: Optional[Dict[str, Any]] = None


def _scan_bpy_capabilities() -> Dict[str, Any]:
    from .capabilities import scan_bpy_capabilities

    return scan_bpy_capabilities()


def _inspect_bpy_scene() -> Dict[str, Any]:
    from .scene import bpy_scene_context, inspect_scene

    return inspect_scene(bpy_scene_context())


def _create_bpy_carrier_mesh(name: str) -> Dict[str, Any]:
    from .scene import bpy_scene_context, create_carrier_mesh

    return create_carrier_mesh(bpy_scene_context(), name)


def _implemented_operations() -> Dict[str, Any]:
    from .capabilities import IMPLEMENTED_OPERATIONS

    return {"supported_operations": sorted(IMPLEMENTED_OPERATIONS)}


def _validate_batch(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    if executor is None:
        raise BlendexError("BLENDER_NOT_CONNECTED", "Batch validation requires a Blender executor.")
    from .safety import validate_operations

    return validate_operations(request.params["operations"], executor)


def _dry_run(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    if executor is None:
        raise BlendexError("BLENDER_NOT_CONNECTED", "Dry run requires a Blender executor.")
    from .safety import dry_run_operations

    return dry_run_operations(request.params["operations"], executor)


def _execute_batch(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    if executor is None:
        raise BlendexError("BLENDER_NOT_CONNECTED", "Batch execution requires a Blender executor.")
    from .batches import execute_batch

    return execute_batch(request, executor)


def _batch_history(request: OperationRequest) -> Dict[str, Any]:
    limit = request.params.get("limit", 20)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        limit = 20
    return {"batches": [record.to_dict() for record in STATE.recent_batches(limit)]}


def _inspect_batch(request: OperationRequest) -> Dict[str, Any]:
    batch_id = request.params["batch_id"]
    record = STATE.batch_history.find(batch_id)
    if record is None:
        raise BlendexError("BATCH_NOT_FOUND", f"Batch not found: {batch_id}")
    return record.to_dict()


def dispatch_payload(
    payload: Any,
    executor: Any,
    capability_scanner: Optional[Callable[[], Dict[str, Any]]] = None,
    scene_inspector: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    request_id = "unknown"
    operation = ""
    try:
        if not isinstance(payload, dict):
            raise BlendexError("VALIDATION_FAILED", "Request payload must be an object.")
        request_id = str(payload.get("id", "unknown"))
        operation = str(payload.get("type", ""))
        request = OperationRequest.from_dict(payload)
        validate_request(request)
        if request.type == "capabilities.scan":
            scanner = capability_scanner or _scan_bpy_capabilities
            result = scanner()
        elif request.type == "capabilities.supported_operations":
            result = _implemented_operations()
        elif request.type == "scene.inspect":
            inspector = scene_inspector or _inspect_bpy_scene
            result = inspector()
        elif request.type == "scene.create_carrier_mesh":
            result = _create_bpy_carrier_mesh(request.params.get("name", "BlendeX Carrier"))
        elif request.type == "safety.validate_batch":
            result = _validate_batch(request, executor)
        elif request.type == "safety.dry_run":
            result = _dry_run(request, executor)
        elif request.type == "safety.execute_batch":
            result = _execute_batch(request, executor)
        elif request.type == "safety.batch_history":
            result = _batch_history(request)
        elif request.type == "safety.inspect_batch":
            result = _inspect_batch(request)
        elif executor is None:
            result = {"validated": True}
        else:
            result = executor.execute(request)
        STATE.record(OperationLog(request_id=request.id, operation=request.type, ok=True, message="OK"))
        return OperationResponse.success(request.id, result).to_dict()
    except BlendexError as error:
        STATE.record(
            OperationLog(
                request_id=request_id,
                operation=operation,
                ok=False,
                message=error.message,
                error_code=error.code,
            )
        )
        return OperationResponse.error(request_id, error).to_dict()
    except Exception as error:
        _LOGGER.exception("Unexpected BlendeX executor failure.")
        blendex_error = BlendexError("EXECUTION_FAILED", str(error) or error.__class__.__name__)
        STATE.record(
            OperationLog(
                request_id=request_id,
                operation=operation,
                ok=False,
                message=blendex_error.message,
                error_code=blendex_error.code,
            )
        )
        return OperationResponse.error(request_id, blendex_error).to_dict()


def _dispatch_payload_with_factory(payload: Any, executor_factory: Callable[[], Any]) -> Dict[str, Any]:
    if isinstance(payload, dict) and payload.get("type") in {
        "capabilities.scan",
        "capabilities.supported_operations",
        "scene.create_carrier_mesh",
        "scene.inspect",
    }:
        return dispatch_payload(payload, executor=None)
    return dispatch_payload(payload, executor=executor_factory())


def _dispatch_payload_for_service(
    payload: Any,
    executor_factory: Callable[[], Any] = None,
    timeout: float = _MAIN_THREAD_DISPATCH_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    if executor_factory is None:
        executor_factory = _default_executor
    if _stop_event.is_set():
        request_id = str(payload.get("id", "unknown")) if isinstance(payload, dict) else "unknown"
        return OperationResponse.error(
            request_id,
            BlendexError("EXECUTION_FAILED", "BlendeX service is stopping."),
        ).to_dict()
    if not _main_thread_dispatch_enabled:
        request_id = str(payload.get("id", "unknown")) if isinstance(payload, dict) else "unknown"
        return OperationResponse.error(
            request_id,
            BlendexError("EXECUTION_FAILED", "BlendeX main-thread dispatch is unavailable."),
        ).to_dict()
    task = _MainThreadDispatchTask(payload, executor_factory)
    _main_thread_dispatch_queue.put(task)
    if not task.event.wait(timeout):
        request_id = str(payload.get("id", "unknown")) if isinstance(payload, dict) else "unknown"
        return OperationResponse.error(
            request_id,
            BlendexError(
                "EXECUTION_FAILED",
                "Timed out waiting for Blender main-thread dispatch.",
            ),
        ).to_dict()
    if task.response is None:
        request_id = str(payload.get("id", "unknown")) if isinstance(payload, dict) else "unknown"
        return OperationResponse.error(
            request_id,
            BlendexError("EXECUTION_FAILED", "Blender main-thread dispatch did not return a response."),
        ).to_dict()
    return task.response


def _drain_main_thread_dispatch() -> Optional[float]:
    while True:
        try:
            task = _main_thread_dispatch_queue.get_nowait()
        except queue.Empty:
            break
        try:
            task.response = _dispatch_payload_with_factory(task.payload, task.executor_factory)
        except Exception as error:
            request_id = str(task.payload.get("id", "unknown")) if isinstance(task.payload, dict) else "unknown"
            task.response = OperationResponse.error(
                request_id,
                BlendexError("EXECUTION_FAILED", str(error) or error.__class__.__name__),
            ).to_dict()
        finally:
            task.event.set()
    if _stop_event.is_set():
        return None
    return 0.05


def _clear_main_thread_dispatch_queue() -> None:
    while True:
        try:
            task = _main_thread_dispatch_queue.get_nowait()
        except queue.Empty:
            break
        task.response = OperationResponse.error(
            "unknown",
            BlendexError("EXECUTION_FAILED", "BlendeX service stopped before dispatch completed."),
        ).to_dict()
        task.event.set()


def _register_main_thread_dispatch_timer() -> bool:
    global _main_thread_dispatch_enabled
    try:
        import bpy
    except ImportError:
        _main_thread_dispatch_enabled = False
        return False
    timers = getattr(getattr(bpy, "app", None), "timers", None)
    register = getattr(timers, "register", None)
    if not callable(register):
        _main_thread_dispatch_enabled = False
        return False
    register(_drain_main_thread_dispatch)
    _main_thread_dispatch_enabled = True
    return True


def start_service(port: Optional[int] = None) -> None:
    global _server_thread, _startup_error
    if STATE.service_running:
        return
    if port is not None:
        STATE.port = port
    _stop_event.clear()
    _startup_event.clear()
    _startup_error = None
    _register_main_thread_dispatch_timer()
    _server_thread = threading.Thread(target=_run_socket_server, daemon=True)
    _server_thread.start()
    if not _startup_event.wait(_STARTUP_TIMEOUT_SECONDS):
        _stop_event.set()
        STATE.service_running = False
        raise BlendexError("EXECUTION_FAILED", "BlendeX service startup timed out.")
    if _startup_error is not None:
        STATE.service_running = False
        raise _startup_error
    STATE.service_running = True


def stop_service() -> None:
    global _server_thread, _main_thread_dispatch_enabled
    _stop_event.set()
    _main_thread_dispatch_enabled = False
    _clear_main_thread_dispatch_queue()
    with _socket_lock:
        sockets = (_active_client_socket, _server_socket)
    for sock in sockets:
        if sock is None:
            continue
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass
    if _server_thread is not None and threading.current_thread() is not _server_thread:
        _server_thread.join(_SHUTDOWN_JOIN_SECONDS)
        if not _server_thread.is_alive():
            _server_thread = None
    STATE.service_running = False
    STATE.client_connected = False
    STATE.client_authenticated = False


def _default_executor() -> Any:
    import bpy

    from .capabilities import scan_bpy_capabilities
    from .executor import GeometryNodesExecutor

    capabilities = scan_bpy_capabilities()
    context = getattr(bpy, "context", None)
    scene_objects = getattr(getattr(context, "scene", None), "objects", None)
    view_layer_objects = getattr(getattr(context, "view_layer", None), "objects", None)

    class BpyExecutionContext:
        objects = scene_objects or view_layer_objects or bpy.data.objects
        node_types = set(capabilities["node_types"].keys())

    return GeometryNodesExecutor(BpyExecutionContext())


def _websocket_accept_key(client_key: str) -> str:
    websocket_guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    digest = hashlib.sha1((client_key + websocket_guid).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


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


def _read_http_headers(conn: socket.socket) -> Tuple[Dict[str, str], bytes]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(1024)
        if not chunk:
            break
        data += chunk
    header_bytes, separator, remaining = data.partition(b"\r\n\r\n")
    if separator:
        header_bytes += separator
    lines = header_bytes.decode("utf-8").split("\r\n")
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return headers, remaining


def _send_handshake(conn: socket.socket, headers: Dict[str, str]) -> None:
    try:
        _validate_auth_headers(headers)
    except BlendexError as error:
        response = (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Length: 0\r\n"
            f"X-BlendeX-Error: {error.code}\r\n\r\n"
        )
        conn.sendall(response.encode("utf-8"))
        raise
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


def _read_exact(conn: socket.socket, size: int, buffer: Optional[bytearray] = None) -> bytes:
    data = b""
    if buffer:
        data = bytes(buffer[:size])
        del buffer[:size]
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError("WebSocket connection closed.")
        data += chunk
    return data


def _read_ws_text(conn: socket.socket, buffer: Optional[bytearray] = None) -> Optional[str]:
    first, second = _read_exact(conn, 2, buffer)
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if opcode == 0x8:
        return None
    if length == 126:
        length = struct.unpack("!H", _read_exact(conn, 2, buffer))[0]
    elif length == 127:
        length = struct.unpack("!Q", _read_exact(conn, 8, buffer))[0]
    mask = _read_exact(conn, 4, buffer) if masked else b""
    payload = bytearray(_read_exact(conn, length, buffer))
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
    global _server_socket, _active_client_socket, _startup_error
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", STATE.port))
            server.listen(1)
            server.settimeout(_SOCKET_TIMEOUT_SECONDS)
            with _socket_lock:
                _server_socket = server
            _startup_event.set()
            while not _stop_event.is_set():
                try:
                    conn, _addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if _stop_event.is_set():
                        break
                    raise
                with conn:
                    conn.settimeout(_SOCKET_TIMEOUT_SECONDS)
                    with _socket_lock:
                        _active_client_socket = conn
                    STATE.client_connected = True
                    try:
                        headers, remaining = _read_http_headers(conn)
                        _send_handshake(conn, headers)
                        buffer = bytearray(remaining)
                        while not _stop_event.is_set():
                            try:
                                text = _read_ws_text(conn, buffer)
                            except socket.timeout:
                                continue
                            if text is None:
                                break
                            payload = json.loads(text)
                            if _stop_event.is_set():
                                break
                            response = _dispatch_payload_for_service(payload)
                            _send_ws_text(conn, json.dumps(response))
                    except socket.timeout:
                        if not _stop_event.is_set():
                            _LOGGER.exception("BlendeX client socket timed out.")
                    except BlendexError as error:
                        if not _stop_event.is_set():
                            _LOGGER.warning(
                                "BlendeX client authentication failed: %s",
                                error.code,
                            )
                    except Exception:
                        if not _stop_event.is_set():
                            _LOGGER.exception("BlendeX client handling failed.")
                    finally:
                        STATE.client_connected = False
                        STATE.client_authenticated = False
                        with _socket_lock:
                            if _active_client_socket is conn:
                                _active_client_socket = None
        except OSError as error:
            _startup_error = BlendexError("EXECUTION_FAILED", f"Could not start BlendeX service: {error}")
            _startup_event.set()
        finally:
            with _socket_lock:
                if _server_socket is server:
                    _server_socket = None
                _active_client_socket = None
            STATE.service_running = False
            STATE.client_connected = False
            STATE.client_authenticated = False
