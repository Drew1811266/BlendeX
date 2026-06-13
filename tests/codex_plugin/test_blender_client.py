import base64
import hashlib
import os
import unittest

from codex_plugin.blendex_mcp.blender_client import BlenderClient, BlenderConnectionConfig


class FakeHandshakeSocket:
    def __init__(self, *, status: str = "101 Switching Protocols", accept_override=None):
        self.status = status
        self.accept_override = accept_override
        self.sent = b""

    def sendall(self, data):
        self.sent += data

    def recv(self, size):
        request = self.sent.decode("utf-8")
        key = ""
        for line in request.splitlines():
            if line.startswith("Sec-WebSocket-Key: "):
                key = line.split(": ", 1)[1]
                break
        accept = self.accept_override
        if accept is None:
            digest = hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
            accept = base64.b64encode(digest).decode("ascii")
        return (
            f"HTTP/1.1 {self.status}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode("utf-8")


class SplitHandshakeSocket(FakeHandshakeSocket):
    def __init__(self):
        super().__init__()
        self.response = None

    def recv(self, size):
        if self.response is None:
            self.response = bytearray(super().recv(size))
        chunk = self.response[:7]
        del self.response[:7]
        return bytes(chunk)


class CaptureSocket:
    def __init__(self):
        self.sent = b""

    def sendall(self, data):
        self.sent += data


class ReadSocket:
    def __init__(self, data):
        self.data = bytearray(data)

    def recv(self, size):
        chunk = self.data[:size]
        del self.data[:size]
        return bytes(chunk)


class BlenderClientTests(unittest.TestCase):
    def setUp(self):
        self.original_session_token = os.environ.pop("BLENDEX_SESSION_TOKEN", None)
        self.original_token = os.environ.pop("BLENDEX_TOKEN", None)

    def tearDown(self):
        if self.original_session_token is not None:
            os.environ["BLENDEX_SESSION_TOKEN"] = self.original_session_token
        if self.original_token is not None:
            os.environ["BLENDEX_TOKEN"] = self.original_token

    def test_default_config_points_to_local_service(self):
        config = BlenderConnectionConfig()

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8765)
        self.assertEqual(config.timeout_seconds, 5.0)

    def test_client_uses_default_config_when_none_is_provided(self):
        client = BlenderClient()

        self.assertEqual(client.config, BlenderConnectionConfig())

    def test_handshake_accepts_valid_websocket_response(self):
        client = BlenderClient()
        sock = FakeHandshakeSocket()

        client._handshake(sock)

        self.assertIn(b"Sec-WebSocket-Key:", sock.sent)

    def test_handshake_sends_configured_session_token(self):
        client = BlenderClient(BlenderConnectionConfig(session_token="secret-token"))
        sock = FakeHandshakeSocket()

        client._handshake(sock)

        self.assertIn(b"X-BlendeX-Token: secret-token\r\n", sock.sent)

    def test_handshake_reads_split_response_headers(self):
        client = BlenderClient()
        sock = SplitHandshakeSocket()

        client._handshake(sock)

        self.assertIn(b"Sec-WebSocket-Key:", sock.sent)

    def test_handshake_rejects_invalid_status(self):
        client = BlenderClient()

        with self.assertRaises(ConnectionError):
            client._handshake(FakeHandshakeSocket(status="200 OK"))

    def test_handshake_rejects_invalid_accept_header(self):
        client = BlenderClient()

        with self.assertRaises(ConnectionError):
            client._handshake(FakeHandshakeSocket(accept_override="bad-accept"))

    def test_send_text_produces_masked_client_frame(self):
        client = BlenderClient()
        sock = CaptureSocket()

        client._send_text(sock, "hello")

        self.assertEqual(sock.sent[0], 0x81)
        self.assertTrue(sock.sent[1] & 0x80)
        self.assertEqual(sock.sent[1] & 0x7F, 5)
        mask = sock.sent[2:6]
        masked_payload = sock.sent[6:]
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(masked_payload))
        self.assertEqual(payload, b"hello")

    def test_read_text_reads_unmasked_server_frame(self):
        client = BlenderClient()
        payload = b"hello"
        sock = ReadSocket(bytes([0x81, len(payload)]) + payload)

        self.assertEqual(client._read_text(sock), "hello")


if __name__ == "__main__":
    unittest.main()
