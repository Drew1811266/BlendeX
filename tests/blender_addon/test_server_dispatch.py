import importlib
import socket
import sys
import time
import types
import unittest

from blendex_protocol.errors import BlendexError

from blender_addon.blendex import server
from blender_addon.blendex.server import (
    _read_http_headers,
    _read_ws_text,
    _send_ws_text,
    _websocket_accept_key,
    dispatch_payload,
)
from blender_addon.blendex.state import STATE


class FakeSocket:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def recv(self, size):
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        self._chunks.insert(0, chunk[size:])
        return chunk[:size]


class DispatchTests(unittest.TestCase):
    def setUp(self):
        STATE.recent_logs.clear()

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

    def test_dispatch_rejects_non_dict_payload_as_json_response(self):
        response = dispatch_payload(["not", "an", "object"], executor=None)

        self.assertFalse(response["ok"])
        self.assertEqual(response["id"], "unknown")
        self.assertEqual(response["error"]["code"], "VALIDATION_FAILED")
        self.assertEqual(STATE.recent_logs[0].error_code, "VALIDATION_FAILED")

    def test_dispatch_converts_executor_exception_to_json_response(self):
        class RaisingExecutor:
            def execute(self, request):
                raise RuntimeError("boom")

        with self.assertLogs(server._LOGGER, level="ERROR"):
            response = dispatch_payload(
                {"id": "req_run", "type": "scene.inspect", "target": {}, "params": {}},
                executor=RaisingExecutor(),
            )

        self.assertFalse(response["ok"])
        self.assertEqual(response["id"], "req_run")
        self.assertEqual(response["error"]["code"], "EXECUTION_FAILED")
        self.assertEqual(STATE.recent_logs[0].request_id, "req_run")
        self.assertEqual(STATE.recent_logs[0].operation, "scene.inspect")
        self.assertEqual(STATE.recent_logs[0].error_code, "EXECUTION_FAILED")


class WebSocketTests(unittest.TestCase):
    def test_websocket_accept_key_matches_rfc_example(self):
        self.assertEqual(
            _websocket_accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        )

    def test_read_http_headers_preserves_trailing_bytes(self):
        headers, remaining = _read_http_headers(
            FakeSocket(
                [
                    b"GET / HTTP/1.1\r\nSec-WebSocket-Key: abc\r\n\r\n\x81\x05hello",
                ]
            )
        )

        self.assertEqual(headers["sec-websocket-key"], "abc")
        self.assertEqual(remaining, b"\x81\x05hello")

    def test_send_and_read_ws_text_round_trips_with_socketpair(self):
        left, right = socket.socketpair()
        try:
            _send_ws_text(left, "hello BlendeX")
            self.assertEqual(_read_ws_text(right), "hello BlendeX")
        finally:
            left.close()
            right.close()


class LifecycleTests(unittest.TestCase):
    def tearDown(self):
        server.stop_service()
        STATE.recent_logs.clear()

    def test_start_service_bind_failure_leaves_service_stopped(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen(1)
            port = blocker.getsockname()[1]

            with self.assertRaises(BlendexError) as raised:
                server.start_service(port)

        self.assertEqual(raised.exception.code, "EXECUTION_FAILED")
        self.assertFalse(STATE.service_running)
        self.assertFalse(STATE.client_connected)

    def test_stop_service_clears_active_client_and_joins_thread(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

        server.start_service(port)
        client = socket.create_connection(("127.0.0.1", port), timeout=1)
        try:
            for _ in range(20):
                if STATE.client_connected:
                    break
                time.sleep(0.05)
            self.assertTrue(STATE.client_connected)

            server.stop_service()

            self.assertFalse(STATE.service_running)
            self.assertFalse(STATE.client_connected)
            self.assertIsNone(server._server_thread)
        finally:
            client.close()


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.original_bpy = sys.modules.get("bpy")

        fake_bpy = types.SimpleNamespace(
            types=types.SimpleNamespace(Operator=object, Panel=object),
            utils=types.SimpleNamespace(register_class=lambda cls: None, unregister_class=lambda cls: None),
        )
        sys.modules["bpy"] = fake_bpy
        import blender_addon.blendex as blendex

        self.blendex = importlib.reload(blendex)

    def tearDown(self):
        if self.original_bpy is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = self.original_bpy
        importlib.reload(self.blendex)

    def test_load_classes_returns_same_operator_classes_each_call(self):
        first = self.blendex._load_classes()
        second = self.blendex._load_classes()

        self.assertIs(first[0], second[0])
        self.assertIs(first[1], second[1])


if __name__ == "__main__":
    unittest.main()
