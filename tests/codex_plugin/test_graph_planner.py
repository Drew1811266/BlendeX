import unittest

from codex_plugin.blendex_mcp.graph_planner import plan_graph


class GraphPlannerTests(unittest.TestCase):
    def test_plan_graph_generates_scatter_graph_without_recipe_id(self):
        result = plan_graph(
            "scatter uneven small pebbles across a sloped ground surface with random scale"
        )

        self.assertEqual(result["mode"], "graph_plan")
        self.assertNotIn("recipe_id", result)
        self.assertEqual(result["intent"]["primary_effect"], "scatter")
        self.assertIn("GeometryNodeDistributePointsOnFaces", result["node_types"])
        self.assertIn("GeometryNodeInstanceOnPoints", result["node_types"])
        self.assertIn("GeometryNodeRealizeInstances", result["node_types"])
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["repairs"], [])
        self.assertTrue(any(operation["type"] == "geometry_nodes.create_node" for operation in result["operations"]))
        self.assertIn("semantic", result["explanation"].lower())

    def test_plan_graph_generates_material_selection_graph(self):
        result = plan_graph("assign a different material to upper faces based on height")

        self.assertEqual(result["mode"], "graph_plan")
        self.assertEqual(result["intent"]["primary_effect"], "material")
        self.assertIn("GeometryNodeSetMaterial", result["node_types"])
        self.assertTrue(result["validation"]["valid"])

    def test_plan_graph_rejects_unsupported_intent(self):
        result = plan_graph("make a fluid simulation with particles over 120 frames")

        self.assertEqual(result["mode"], "unsupported")
        self.assertEqual(result["error"]["code"], "PLANNER_UNSUPPORTED_REQUEST")
        self.assertIn("simulation_zones_out_of_scope", result["error"]["details"]["unsupported_reasons"])


if __name__ == "__main__":
    unittest.main()
