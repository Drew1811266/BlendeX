import unittest

from codex_plugin.blendex_mcp.graph_ir import add_link, add_node, new_graph
from codex_plugin.blendex_mcp.graph_validation import validate_graph


def _socket(name, socket_type, direction, *, is_field=False, is_multi_input=False):
    return {
        "name": name,
        "identifier": name,
        "socket_type": socket_type,
        "direction": direction,
        "is_multi_input": is_multi_input,
        "is_field": is_field,
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
        "GeometryNodeDistributePointsOnFaces": {
            "inputs": [_socket("Mesh", "NodeSocketGeometry", "input"), _socket("Density", "NodeSocketFloat", "input", is_field=True)],
            "outputs": [_socket("Points", "NodeSocketGeometry", "output")],
        },
        "GeometryNodeInstanceOnPoints": {
            "inputs": [_socket("Points", "NodeSocketGeometry", "input")],
            "outputs": [_socket("Instances", "NodeSocketGeometry", "output")],
        },
        "GeometryNodeRealizeInstances": {
            "inputs": [_socket("Geometry", "NodeSocketGeometry", "input")],
            "outputs": [_socket("Geometry", "NodeSocketGeometry", "output")],
        },
        "GeometryNodeSetPosition": {
            "inputs": [_socket("Geometry", "NodeSocketGeometry", "input"), _socket("Offset", "NodeSocketVector", "input", is_field=True)],
            "outputs": [_socket("Geometry", "NodeSocketGeometry", "output")],
        },
        "FunctionNodeRandomValue": {
            "inputs": [],
            "outputs": [_socket("Value", "NodeSocketFloat", "output", is_field=True)],
        },
        "ValueSinkNode": {
            "inputs": [_socket("Value", "NodeSocketFloat", "input", is_field=False)],
            "outputs": [],
        },
    }
}


class GraphValidationTests(unittest.TestCase):
    def test_validation_accepts_valid_scatter_graph(self):
        graph = new_graph("Valid Scatter")
        add_node(graph, "input", "NodeGroupInput")
        add_node(graph, "points", "GeometryNodeDistributePointsOnFaces")
        add_node(graph, "instances", "GeometryNodeInstanceOnPoints")
        add_node(graph, "realize", "GeometryNodeRealizeInstances")
        add_node(graph, "output", "NodeGroupOutput")
        add_link(graph, "input", "Geometry", "points", "Mesh")
        add_link(graph, "points", "Points", "instances", "Points")
        add_link(graph, "instances", "Instances", "realize", "Geometry")
        add_link(graph, "realize", "Geometry", "output", "Geometry")

        result = validate_graph(graph, CAPABILITIES)

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_validation_rejects_missing_group_output(self):
        graph = new_graph("Missing Output")
        add_node(graph, "input", "NodeGroupInput")

        result = validate_graph(graph, CAPABILITIES)

        self.assertFalse(result["valid"])
        self.assertIn("MISSING_GROUP_OUTPUT", {error["code"] for error in result["errors"]})

    def test_validation_rejects_unknown_link_node(self):
        graph = new_graph("Broken Link")
        add_node(graph, "output", "NodeGroupOutput")
        add_link(graph, "missing", "Geometry", "output", "Geometry")

        result = validate_graph(graph, CAPABILITIES)

        self.assertFalse(result["valid"])
        self.assertIn("UNKNOWN_LINK_NODE", {error["code"] for error in result["errors"]})

    def test_validation_rejects_field_to_non_field_value_socket(self):
        graph = new_graph("Field Mismatch")
        add_node(graph, "random", "FunctionNodeRandomValue")
        add_node(graph, "sink", "ValueSinkNode")
        add_node(graph, "output", "NodeGroupOutput")
        add_link(graph, "random", "Value", "sink", "Value")

        result = validate_graph(graph, CAPABILITIES)

        self.assertFalse(result["valid"])
        self.assertIn("FIELD_VALUE_MISMATCH", {error["code"] for error in result["errors"]})

    def test_validation_rejects_instances_into_set_position_without_realize(self):
        graph = new_graph("Instance Edit")
        add_node(graph, "instances", "GeometryNodeInstanceOnPoints")
        add_node(graph, "set_position", "GeometryNodeSetPosition")
        add_node(graph, "output", "NodeGroupOutput")
        add_link(graph, "instances", "Instances", "set_position", "Geometry")
        add_link(graph, "set_position", "Geometry", "output", "Geometry")

        result = validate_graph(graph, CAPABILITIES)

        self.assertFalse(result["valid"])
        self.assertIn("INSTANCE_REQUIRES_REALIZE", {error["code"] for error in result["errors"]})


if __name__ == "__main__":
    unittest.main()
