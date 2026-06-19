import unittest

from codex_plugin.blendex_mcp.graph_ir import add_link, add_node, new_graph
from codex_plugin.blendex_mcp.graph_repair import repair_graph


def _socket(name, socket_type, direction):
    return {
        "name": name,
        "identifier": name,
        "socket_type": socket_type,
        "direction": direction,
        "is_multi_input": False,
        "is_field": False,
        "default_value": None,
        "enum_items": [],
    }


CAPABILITIES = {
    "node_types": {
        "NodeGroupInput": {
            "inputs": [],
            "outputs": [_socket("Geometry", "NodeSocketGeometry", "output")],
        },
        "NodeGroupOutput": {
            "inputs": [_socket("Geometry", "NodeSocketGeometry", "input")],
            "outputs": [],
        },
        "GeometryNodeSetPosition": {
            "inputs": [_socket("Geometry", "NodeSocketGeometry", "input")],
            "outputs": [_socket("Geometry", "NodeSocketGeometry", "output")],
        },
        "GeometryNodeInstanceOnPoints": {
            "inputs": [],
            "outputs": [_socket("Instances", "NodeSocketGeometry", "output")],
        },
        "GeometryNodeRealizeInstances": {
            "inputs": [_socket("Geometry", "NodeSocketGeometry", "input")],
            "outputs": [_socket("Geometry", "NodeSocketGeometry", "output")],
        },
    }
}


class GraphRepairTests(unittest.TestCase):
    def test_repair_adds_missing_group_output_and_final_link(self):
        graph = new_graph("Missing Output")
        add_node(graph, "input", "NodeGroupInput")

        result = repair_graph(graph, CAPABILITIES)

        self.assertTrue(result["validation"]["valid"])
        self.assertTrue(result["repaired"])
        self.assertIn("ADD_GROUP_OUTPUT", [entry["code"] for entry in result["repairs"]])
        self.assertTrue(
            any(link["to_node"] == "group_output" and link["to_socket"] == "Geometry" for link in result["graph"]["links"])
        )

    def test_repair_normalizes_socket_name_drift_from_capabilities(self):
        graph = new_graph("Socket Drift")
        add_node(graph, "input", "NodeGroupInput")
        add_node(graph, "output", "NodeGroupOutput")
        add_link(graph, "input", "geometry", "output", "geometry")

        result = repair_graph(graph, CAPABILITIES)

        self.assertTrue(result["validation"]["valid"])
        self.assertIn("NORMALIZE_SOCKET_NAME", [entry["code"] for entry in result["repairs"]])
        self.assertEqual(result["graph"]["links"][0]["from_socket"], "Geometry")
        self.assertEqual(result["graph"]["links"][0]["to_socket"], "Geometry")

    def test_repair_inserts_realize_instances_before_set_position(self):
        graph = new_graph("Instance Edit")
        add_node(graph, "instances", "GeometryNodeInstanceOnPoints")
        add_node(graph, "set_position", "GeometryNodeSetPosition")
        add_node(graph, "output", "NodeGroupOutput")
        add_link(graph, "instances", "Instances", "set_position", "Geometry")
        add_link(graph, "set_position", "Geometry", "output", "Geometry")

        result = repair_graph(graph, CAPABILITIES)

        self.assertTrue(result["validation"]["valid"])
        self.assertIn("INSERT_REALIZE_INSTANCES", [entry["code"] for entry in result["repairs"]])
        node_types = {node["node_type"] for node in result["graph"]["nodes"]}
        self.assertIn("GeometryNodeRealizeInstances", node_types)
        self.assertFalse(
            any(
                link["from_node"] == "instances" and link["to_node"] == "set_position"
                for link in result["graph"]["links"]
            )
        )


if __name__ == "__main__":
    unittest.main()
