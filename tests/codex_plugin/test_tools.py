import unittest

from codex_plugin.blendex_mcp.tools import tool_names, tool_to_operation


class ToolMappingTests(unittest.TestCase):
    def test_tool_names_include_core_graph_tools(self):
        names = tool_names()

        self.assertIn("blendex_create_node", names)
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


if __name__ == "__main__":
    unittest.main()
