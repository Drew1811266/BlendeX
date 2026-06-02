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
        STATE.record(
            OperationLog(
                request_id=request_id,
                operation=str(payload.get("type", "")),
                ok=False,
                message=error.message,
                error_code=error.code,
            )
        )
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
