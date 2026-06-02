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
