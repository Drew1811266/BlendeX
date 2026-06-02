import importlib
import socket
import sys
import threading
import time
import types
import unittest

from blendex_protocol.errors import BlendexError

from blender_addon.blendex import server
from blender_addon.blendex.server import (
    _read_http_headers,
    _read_ws_text,
    _dispatch_payload_for_service,
    _drain_main_thread_dispatch,
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
                {
                    "id": "req_run",
                    "type": "geometry_nodes.inspect_tree",
                    "target": {"object_id": "Cube"},
                    "params": {},
                },
                executor=RaisingExecutor(),
            )

        self.assertFalse(response["ok"])
        self.assertEqual(response["id"], "req_run")
        self.assertEqual(response["error"]["code"], "EXECUTION_FAILED")
        self.assertEqual(STATE.recent_logs[0].request_id, "req_run")
        self.assertEqual(STATE.recent_logs[0].operation, "geometry_nodes.inspect_tree")
        self.assertEqual(STATE.recent_logs[0].error_code, "EXECUTION_FAILED")

    def test_dispatch_handles_capability_scan_without_executor(self):
        response = dispatch_payload(
            {"id": "req_scan", "type": "capabilities.scan", "target": {}, "params": {}},
            executor=None,
            capability_scanner=lambda: {
                "blender_version": [4, 2, 0],
                "node_types": {"GeometryNodeJoinGeometry": {}},
                "supported_operations": ["capabilities.scan"],
            },
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["blender_version"], [4, 2, 0])
        self.assertIn("GeometryNodeJoinGeometry", response["result"]["node_types"])

    def test_dispatch_handles_scene_inspect_without_executor(self):
        response = dispatch_payload(
            {"id": "req_scene", "type": "scene.inspect", "target": {}, "params": {}},
            executor=None,
            scene_inspector=lambda: {"objects": [{"name": "Cube"}], "selected_object": "Cube"},
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["selected_object"], "Cube")


class MainThreadDispatchTests(unittest.TestCase):
    def setUp(self):
        server._stop_event.clear()

    def tearDown(self):
        server._main_thread_dispatch_enabled = False
        server._clear_main_thread_dispatch_queue()
        server._stop_event.clear()

    def test_service_dispatch_defers_execution_until_main_thread_drain(self):
        calls = []

        class RecordingExecutor:
            def execute(self, request):
                calls.append(threading.current_thread().name)
                return {"thread": calls[-1]}

        def executor_factory():
            calls.append("factory")
            return RecordingExecutor()

        server._main_thread_dispatch_enabled = True
        response_holder = []
        payload = {
            "id": "req_thread",
            "type": "geometry_nodes.inspect_tree",
            "target": {"object_id": "Cube"},
            "params": {},
        }

        worker = threading.Thread(
            target=lambda: response_holder.append(
                _dispatch_payload_for_service(payload, executor_factory=executor_factory, timeout=1.0)
            ),
            name="socket-worker",
        )
        worker.start()
        for _ in range(20):
            if server._main_thread_dispatch_queue.qsize():
                break
            time.sleep(0.01)

        self.assertEqual(calls, [])

        _drain_main_thread_dispatch()
        worker.join(1.0)

        self.assertEqual(calls, ["factory", "MainThread"])
        self.assertTrue(response_holder[0]["ok"])

    def test_service_dispatch_returns_error_without_executor_after_stop(self):
        calls = []

        def executor_factory():
            calls.append("factory")

            class RecordingExecutor:
                def execute(self, request):
                    calls.append("execute")
                    return {"ok": True}

            return RecordingExecutor()

        server._main_thread_dispatch_enabled = False
        server._stop_event.set()
        response = _dispatch_payload_for_service(
            {
                "id": "req_stopped",
                "type": "geometry_nodes.inspect_tree",
                "target": {"object_id": "Cube"},
                "params": {},
            },
            executor_factory=executor_factory,
        )

        self.assertEqual(calls, [])
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "EXECUTION_FAILED")

    def test_service_dispatch_requires_main_thread_dispatcher(self):
        calls = []

        def executor_factory():
            calls.append("factory")

            class RecordingExecutor:
                def execute(self, request):
                    calls.append("execute")
                    return {"ok": True}

            return RecordingExecutor()

        server._main_thread_dispatch_enabled = False
        response = _dispatch_payload_for_service(
            {
                "id": "req_no_dispatcher",
                "type": "geometry_nodes.inspect_tree",
                "target": {"object_id": "Cube"},
                "params": {},
            },
            executor_factory=executor_factory,
        )

        self.assertEqual(calls, [])
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "EXECUTION_FAILED")


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
