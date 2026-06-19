import unittest

from codex_plugin.blendex_mcp.graph_ir import (
    add_link,
    add_node,
    graph_to_operations,
    new_graph,
    set_socket_value,
)


class GraphIrTests(unittest.TestCase):
    def test_graph_ir_exports_to_existing_operation_batch_shape(self):
        graph = new_graph("BlendeX Generated Scatter")
        add_node(graph, "group_input", "NodeGroupInput", label="Input", location=[-400, 0])
        add_node(graph, "points", "GeometryNodeDistributePointsOnFaces", label="Points", location=[-180, 0])
        add_node(graph, "instances", "GeometryNodeInstanceOnPoints", label="Instances", location=[40, 0])
        add_node(graph, "realize", "GeometryNodeRealizeInstances", label="Realize", location=[260, 0])
        add_node(graph, "group_output", "NodeGroupOutput", label="Output", location=[480, 0])
        set_socket_value(graph, "points", "Density", 24.0)
        add_link(graph, "group_input", "Geometry", "points", "Mesh")
        add_link(graph, "points", "Points", "instances", "Points")
        add_link(graph, "instances", "Instances", "realize", "Geometry")
        add_link(graph, "realize", "Geometry", "group_output", "Geometry")

        operations = graph_to_operations(graph)

        self.assertEqual(operations[0]["type"], "scene.create_carrier_mesh")
        self.assertEqual(operations[1]["type"], "geometry_nodes.create_modifier")
        self.assertEqual(
            [operation["type"] for operation in operations].count("geometry_nodes.create_node"),
            5,
        )
        self.assertIn(
            {
                "id": "set_points_density",
                "type": "geometry_nodes.set_socket_value",
                "target": {
                    "object_id": "BlendeX Generated Scatter",
                    "modifier_id": "BlendeX Geometry",
                },
                "params": {"node_id": "points", "socket": "Density", "value": 24.0},
            },
            operations,
        )

    def test_graph_ir_keeps_explanation_trace(self):
        graph = new_graph("Explained Graph")
        graph["explanations"].append("Use Distribute Points on Faces for scatter.")

        self.assertEqual(
            graph["explanations"],
            ["Use Distribute Points on Faces for scatter."],
        )


if __name__ == "__main__":
    unittest.main()
