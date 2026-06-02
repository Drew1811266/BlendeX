import base64
import hashlib
import json
import logging
import socket
import struct
import threading
from typing import Any, Dict, Optional, Tuple

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
_LOGGER = logging.getLogger(__name__)


def dispatch_payload(payload: Any, executor: Any) -> Dict[str, Any]:
    request_id = "unknown"
    operation = ""
    try:
        if not isinstance(payload, dict):
            raise BlendexError("VALIDATION_FAILED", "Request payload must be an object.")
        request_id = str(payload.get("id", "unknown"))
        operation = str(payload.get("type", ""))
        request = OperationRequest.from_dict(payload)
        validate_request(request)
        if executor is None:
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


def start_service(port: Optional[int] = None) -> None:
    global _server_thread, _startup_error
    if STATE.service_running:
        return
    if port is not None:
        STATE.port = port
    _stop_event.clear()
    _startup_event.clear()
    _startup_error = None
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
    global _server_thread
    _stop_event.set()
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
                            response = dispatch_payload(payload, executor=_default_executor())
                            _send_ws_text(conn, json.dumps(response))
                    except socket.timeout:
                        if not _stop_event.is_set():
                            _LOGGER.exception("BlendeX client socket timed out.")
                    except Exception:
                        if not _stop_event.is_set():
                            _LOGGER.exception("BlendeX client handling failed.")
                    finally:
                        STATE.client_connected = False
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
