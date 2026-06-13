import unittest

from codex_plugin.blendex_mcp.tools import tool_names, tool_to_operation


class ToolMappingTests(unittest.TestCase):
    def test_tool_names_include_core_graph_tools(self):
        names = tool_names()

        self.assertIn("blendex_create_node", names)
        self.assertIn("blendex_inspect_scene", names)
        self.assertIn("blendex_scan_capabilities", names)

    def test_create_node_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_create_node",
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "node_type": "GeometryNodeJoinGeometry",
                "label": "Join",
            },
            request_id="req_1",
        )

        self.assertEqual(operation["type"], "geometry_nodes.create_node")
        self.assertEqual(operation["target"]["object_id"], "Cube")
        self.assertEqual(operation["params"]["node_type"], "GeometryNodeJoinGeometry")

    def test_tool_names_include_v0_2_graph_kernel_tools(self):
        names = tool_names()

        for name in [
            "blendex_create_carrier_mesh",
            "blendex_create_modifier",
            "blendex_inspect_tree",
            "blendex_set_socket_value",
            "blendex_link_sockets",
            "blendex_label_node",
            "blendex_validate_batch",
            "blendex_dry_run",
            "blendex_execute_confirmed_batch",
        ]:
            self.assertIn(name, names)

    def test_create_modifier_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_create_modifier",
            {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            request_id="req_modifier",
        )

        self.assertEqual(operation["type"], "geometry_nodes.create_modifier")
        self.assertEqual(operation["target"]["object_id"], "Cube")
        self.assertEqual(operation["params"]["modifier_id"], "BlendeX Geometry")

    def test_set_socket_value_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_set_socket_value",
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "node_id": "Value",
                "socket": "Value",
                "value": 3.0,
            },
            request_id="req_value",
        )

        self.assertEqual(operation["type"], "geometry_nodes.set_socket_value")
        self.assertEqual(operation["params"]["value"], 3.0)

    def test_link_sockets_maps_to_structured_operation(self):
        operation = tool_to_operation(
            "blendex_link_sockets",
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "from_node": "Group Input",
                "from_socket": "Geometry",
                "to_node": "Group Output",
                "to_socket": "Geometry",
            },
            request_id="req_link",
        )

        self.assertEqual(operation["type"], "geometry_nodes.link_sockets")
        self.assertEqual(operation["params"]["to_socket"], "Geometry")

    def test_validate_batch_maps_operations_array(self):
        operation = tool_to_operation(
            "blendex_validate_batch",
            {"operations": [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}]},
            request_id="req_batch",
        )

        self.assertEqual(operation["type"], "safety.validate_batch")
        self.assertEqual(operation["params"]["operations"][0]["type"], "scene.inspect")

    def test_execute_confirmed_batch_maps_confirmation_arguments(self):
        operations = [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}]
        preview = {"nodes": []}

        operation = tool_to_operation(
            "blendex_execute_confirmed_batch",
            {
                "operations": operations,
                "confirmation_id": "confirm_1",
                "summary": "Inspect scene",
                "preview": preview,
            },
            request_id="req_execute",
        )

        self.assertEqual(operation["id"], "req_execute")
        self.assertEqual(operation["type"], "safety.execute_batch")
        self.assertEqual(operation["params"]["operations"], operations)
        self.assertTrue(operation["params"]["confirmed"])
        self.assertEqual(operation["params"]["confirmation_id"], "confirm_1")
        self.assertEqual(operation["params"]["summary"], "Inspect scene")
        self.assertEqual(operation["params"]["preview"], preview)

    def test_inspect_scene_maps_to_structured_operation(self):
        operation = tool_to_operation("blendex_inspect_scene", {}, request_id="req_x")

        self.assertEqual(
            operation,
            {"id": "req_x", "type": "scene.inspect", "target": {}, "params": {}},
        )

    def test_unknown_tool_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown BlendeX tool: blendex_nope"):
            tool_to_operation("blendex_nope", {}, request_id="req_unknown")


if __name__ == "__main__":
    unittest.main()
