import base64
import json
import os
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
        with socket.create_connection(
            (self.config.host, self.config.port),
            timeout=self.config.timeout_seconds,
        ) as sock:
            self._handshake(sock)
            self._send_text(sock, json.dumps(operation))
            return json.loads(self._read_text(sock))

    def _handshake(self, sock: socket.socket) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET /blendex HTTP/1.1\r\n"
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
