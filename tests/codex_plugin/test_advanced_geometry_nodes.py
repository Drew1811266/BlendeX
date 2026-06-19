import unittest

from codex_plugin.blendex_mcp.benchmark import fake_geometry_nodes_capabilities, run_heldout_benchmark
from codex_plugin.blendex_mcp.graph_planner import plan_graph


CAPABILITIES = fake_geometry_nodes_capabilities()


def _node_ids_by_type(graph, node_type):
    return [node["id"] for node in graph["nodes"] if node["node_type"] == node_type]


def _has_link(graph, from_type, from_socket, to_type, to_socket):
    nodes = {node["id"]: node for node in graph["nodes"]}
    for link in graph["links"]:
        from_node = nodes[link["from_node"]]
        to_node = nodes[link["to_node"]]
        if (
            from_node["node_type"] == from_type
            and link["from_socket"] == from_socket
            and to_node["node_type"] == to_type
            and link["to_socket"] == to_socket
        ):
            return True
    return False


class AdvancedGeometryNodesTests(unittest.TestCase):
    def test_capture_attribute_reads_position_before_deformation(self):
        result = plan_graph("capture the original position before deforming points upward", CAPABILITIES)
        graph = result["graph"]

        self.assertEqual(result["mode"], "graph_plan")
        self.assertTrue(result["validation"]["valid"], result["validation"])
        self.assertIn("GeometryNodeInputPosition", result["node_types"])
        self.assertIn("GeometryNodeCaptureAttribute", result["node_types"])
        self.assertIn("GeometryNodeSetPosition", result["node_types"])
        self.assertLess(
            _node_ids_by_type(graph, "GeometryNodeCaptureAttribute")[0],
            _node_ids_by_type(graph, "GeometryNodeSetPosition")[0],
        )
        self.assertTrue(_has_link(graph, "GeometryNodeInputPosition", "Position", "GeometryNodeCaptureAttribute", "Value"))
        self.assertTrue(_has_link(graph, "GeometryNodeCaptureAttribute", "Geometry", "GeometryNodeSetPosition", "Geometry"))

    def test_material_variation_stores_random_named_attribute_before_assignment(self):
        result = plan_graph("give repeated window modules random warm and cool material variations", CAPABILITIES)
        graph = result["graph"]

        self.assertEqual(result["mode"], "graph_plan")
        self.assertTrue(result["validation"]["valid"], result["validation"])
        for node_type in (
            "GeometryNodeInstanceOnPoints",
            "GeometryNodeRealizeInstances",
            "FunctionNodeRandomValue",
            "GeometryNodeStoreNamedAttribute",
            "GeometryNodeSetMaterial",
        ):
            self.assertIn(node_type, result["node_types"])
        self.assertTrue(_has_link(graph, "FunctionNodeRandomValue", "Value", "GeometryNodeStoreNamedAttribute", "Value"))
        self.assertTrue(_has_link(graph, "GeometryNodeStoreNamedAttribute", "Geometry", "GeometryNodeSetMaterial", "Geometry"))
        self.assertIn(
            {"node_id": "store_material_variation", "socket": "Name", "value": "material_variation"},
            graph["socket_values"],
        )

    def test_height_based_material_uses_position_selection_mask(self):
        result = plan_graph("assign a different material to upper faces based on height", CAPABILITIES)
        graph = result["graph"]

        self.assertEqual(result["mode"], "graph_plan")
        self.assertTrue(result["validation"]["valid"], result["validation"])
        self.assertIn("GeometryNodeInputPosition", result["node_types"])
        self.assertIn("ShaderNodeSeparateXYZ", result["node_types"])
        self.assertIn("FunctionNodeCompare", result["node_types"])
        self.assertTrue(_has_link(graph, "GeometryNodeInputPosition", "Position", "ShaderNodeSeparateXYZ", "Vector"))
        self.assertTrue(_has_link(graph, "ShaderNodeSeparateXYZ", "Z", "FunctionNodeCompare", "A"))
        self.assertTrue(_has_link(graph, "FunctionNodeCompare", "Result", "GeometryNodeSetMaterial", "Selection"))

    def test_instances_are_realized_before_mesh_only_deformation(self):
        result = plan_graph(
            "place repeated blocks and then realize them so each block can be beveled individually",
            CAPABILITIES,
        )
        graph = result["graph"]

        self.assertEqual(result["mode"], "graph_plan")
        self.assertTrue(result["validation"]["valid"], result["validation"])
        self.assertTrue(_has_link(graph, "GeometryNodeInstanceOnPoints", "Instances", "GeometryNodeRealizeInstances", "Geometry"))
        self.assertTrue(_has_link(graph, "GeometryNodeRealizeInstances", "Geometry", "GeometryNodeSetPosition", "Geometry"))
        self.assertFalse(_has_link(graph, "GeometryNodeInstanceOnPoints", "Instances", "GeometryNodeSetPosition", "Geometry"))

    def test_exposed_group_inputs_are_modeled_and_connected(self):
        result = plan_graph("make the number of generated floors an exposed parameter on the node group", CAPABILITIES)
        graph = result["graph"]

        self.assertEqual(result["mode"], "graph_plan")
        self.assertTrue(result["validation"]["valid"], result["validation"])
        self.assertIn(
            {
                "name": "Floor Count",
                "identifier": "floor_count",
                "socket_type": "NodeSocketInt",
                "default_value": 8,
            },
            graph["group_inputs"],
        )
        self.assertTrue(_has_link(graph, "NodeGroupInput", "Floor Count", "GeometryNodeMeshLine", "Count"))

    def test_heldout_benchmark_all_prompts_meet_effect_and_node_properties(self):
        summary = run_heldout_benchmark()

        self.assertEqual(summary["valid_plan_count"], summary["total"])
        self.assertEqual(summary["property_pass_count"], summary["total"], summary["results"])


if __name__ == "__main__":
    unittest.main()
