import base64
import hashlib
import json
import os
import socket
import struct
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BlenderConnectionConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    timeout_seconds: float = 5.0
    session_token: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "BlenderConnectionConfig":
        return cls(
            session_token=os.environ.get("BLENDEX_SESSION_TOKEN") or os.environ.get("BLENDEX_TOKEN")
        )


class BlenderClient:
    def __init__(self, config: Optional[BlenderConnectionConfig] = None):
        self.config = config or BlenderConnectionConfig.from_environment()

    def send_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        with socket.create_connection(
            (self.config.host, self.config.port),
            timeout=self.config.timeout_seconds,
        ) as sock:
            self._handshake(sock)
            self._send_text(sock, json.dumps(operation))
            return json.loads(self._read_text(sock))

    def _handshake(self, sock: socket.socket) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request_lines = [
            "GET /blendex HTTP/1.1",
            f"Host: {self.config.host}:{self.config.port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
        ]
        if self.config.session_token:
            request_lines.append(f"X-BlendeX-Token: {self.config.session_token}")
        request_lines.append("Sec-WebSocket-Version: 13")
        request = "\r\n".join(request_lines) + "\r\n\r\n"
        sock.sendall(request.encode("utf-8"))
        response_bytes = b""
        while b"\r\n\r\n" not in response_bytes:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("BlendeX service closed during WebSocket handshake.")
            response_bytes += chunk
        response = response_bytes.decode("utf-8", errors="replace")
        lines = response.split("\r\n")
        status_parts = lines[0].split()
        headers = {}
        for line in lines[1:]:
            if not line or ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        if len(status_parts) < 2 or status_parts[0] not in {"HTTP/1.0", "HTTP/1.1"}:
            raise ConnectionError("BlendeX service did not accept WebSocket handshake.")
        if status_parts[1] != "101":
            if status_parts[1] == "401":
                auth_error = headers.get("x-blendex-error", "HTTP 401")
                raise ConnectionError(
                    f"BlendeX authentication failed: {auth_error} (HTTP 401)."
                )
            raise ConnectionError("BlendeX service did not accept WebSocket handshake.")
        digest = hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
        ).digest()
        expected_accept = base64.b64encode(digest).decode("ascii")
        if headers.get("sec-websocket-accept") != expected_accept:
            raise ConnectionError("BlendeX service returned an invalid WebSocket handshake.")

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
