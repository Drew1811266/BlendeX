import json
import unittest

from codex_plugin.blendex_mcp import server


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result or {"ok": True}
        self.error = error
        self.operations = []

    def send_operation(self, operation):
        self.operations.append(operation)
        if self.error is not None:
            raise self.error
        return self.result


class ServerTests(unittest.TestCase):
    def test_handle_message_initializes(self):
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"}, FakeClient()
        )

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertEqual(response["result"]["serverInfo"]["name"], "blendex")

    def test_handle_message_lists_tools(self):
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, FakeClient()
        )

        self.assertEqual(response["id"], 2)
        self.assertIn("tools", response["result"])

    def test_initialized_notification_returns_no_response(self):
        response = server.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}, FakeClient()
        )

        self.assertIsNone(response)
        self.assertIsNone(
            server.handle_line(
                '{"jsonrpc":"2.0","method":"notifications/initialized"}\n',
                FakeClient(),
            )
        )

    def test_invalid_request_shapes_return_invalid_request_error(self):
        invalid_messages = [
            [],
            {"jsonrpc": "2.0", "id": 1},
            {"jsonrpc": "2.0", "id": 1, "method": 3},
            {"id": 1, "method": "tools/list"},
            {"jsonrpc": "1.0", "id": 1, "method": "tools/list"},
        ]

        for message in invalid_messages:
            with self.subTest(message=message):
                response = server.handle_message(message, FakeClient())
                self.assertEqual(response["error"]["code"], -32600)

    def test_tools_call_success_uses_fake_client(self):
        client = FakeClient(result={"created": True})

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "blendex_inspect_scene",
                    "arguments": {},
                },
            },
            client,
        )

        self.assertEqual(response["id"], 3)
        self.assertEqual(json.loads(response["result"]["content"][0]["text"]), {"created": True})
        self.assertEqual(client.operations[0]["type"], "scene.inspect")

    def test_tools_call_invalid_params_returns_invalid_params_error(self):
        invalid_params = [
            [],
            {"name": ""},
            {"name": 3},
            {"name": "blendex_inspect_scene", "arguments": []},
        ]

        for params in invalid_params:
            with self.subTest(params=params):
                response = server.handle_message(
                    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": params},
                    FakeClient(),
                )
                self.assertEqual(response["error"]["code"], -32602)

    def test_tools_call_rejects_arguments_that_violate_tool_schema(self):
        invalid_calls = [
            {
                "name": "blendex_create_node",
                "arguments": {"object_id": 3, "node_type": "GeometryNodeJoinGeometry"},
            },
            {
                "name": "blendex_create_node",
                "arguments": {"object_id": "Cube", "node_type": 3},
            },
            {
                "name": "blendex_create_node",
                "arguments": {
                    "object_id": "Cube",
                    "node_type": "GeometryNodeJoinGeometry",
                    "modifier_id": 3,
                },
            },
            {
                "name": "blendex_create_node",
                "arguments": {
                    "object_id": "Cube",
                    "node_type": "GeometryNodeJoinGeometry",
                    "label": 3,
                },
            },
            {
                "name": "blendex_create_node",
                "arguments": {
                    "object_id": "Cube",
                    "node_type": "GeometryNodeJoinGeometry",
                    "unexpected": "value",
                },
            },
            {"name": "blendex_inspect_scene", "arguments": {"unexpected": "value"}},
            {"name": "blendex_scan_capabilities", "arguments": {"unexpected": "value"}},
        ]

        for params in invalid_calls:
            with self.subTest(params=params):
                response = server.handle_message(
                    {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": params},
                    FakeClient(),
                )
                self.assertEqual(response["error"]["code"], -32602)

    def test_tools_call_rejects_invalid_v0_2_arguments(self):
        invalid_calls = [
            {"name": "blendex_create_modifier", "arguments": {"object_id": 3}},
            {"name": "blendex_link_sockets", "arguments": {"object_id": "Cube"}},
            {
                "name": "blendex_set_socket_value",
                "arguments": {"object_id": "Cube", "node_id": "Value", "socket": "Value"},
            },
            {"name": "blendex_validate_batch", "arguments": {"operations": "not a list"}},
        ]

        for params in invalid_calls:
            with self.subTest(params=params):
                response = server.handle_message(
                    {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": params},
                    FakeClient(),
                )
                self.assertEqual(response["error"]["code"], -32602)

    def test_tools_call_missing_required_mapping_returns_invalid_params_error(self):
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "blendex_create_node",
                    "arguments": {"node_type": "GeometryNodeJoinGeometry"},
                },
            },
            FakeClient(),
        )

        self.assertEqual(response["error"]["code"], -32602)

    def test_unknown_tool_returns_json_rpc_error(self):
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "blendex_nope", "arguments": {}},
            },
            FakeClient(),
        )

        self.assertEqual(response["error"]["code"], -32601)

    def test_connection_failure_returns_server_error(self):
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "blendex_inspect_scene"},
            },
            FakeClient(error=ConnectionError("no blender")),
        )

        self.assertEqual(response["error"]["code"], -32000)
        self.assertIn("no blender", response["error"]["message"])

    def test_tools_call_marks_blender_operation_errors_as_tool_errors(self):
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {"name": "blendex_inspect_scene"},
            },
            FakeClient(
                result={
                    "id": "req_bad",
                    "ok": False,
                    "error": {"code": "UNSUPPORTED_OPERATION", "message": "Nope"},
                }
            ),
        )

        self.assertEqual(response["id"], 9)
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "UNSUPPORTED_OPERATION")

    def test_malformed_json_line_returns_parse_error(self):
        response_line = server.handle_line("not-json\n", FakeClient())
        response = json.loads(response_line)

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIsNone(response["id"])
        self.assertEqual(response["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
