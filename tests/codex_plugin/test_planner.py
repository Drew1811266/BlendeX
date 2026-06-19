import unittest

from codex_plugin.blendex_mcp.planner import plan_goal


class PlannerTests(unittest.TestCase):
    def test_planner_prefers_grid_tower_recipe(self):
        result = plan_goal("create a modular grid tower", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "architecture.grid_tower")
        self.assertEqual(result["operations"][0]["type"], "scene.create_carrier_mesh")
        self.assertIn("Matched recipe", result["message"])

    def test_planner_prefers_stone_scatter_recipe(self):
        result = plan_goal("scatter stones on a ground patch", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.stones")
        self.assertTrue(any(operation["type"] == "geometry_nodes.create_node" for operation in result["operations"]))

    def test_planner_prefers_wall_panel_recipe(self):
        result = plan_goal("make a procedural facade wall panel", capabilities=None)

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "architecture.wall_panel")

    def test_planner_prefers_grass_recipe(self):
        result = plan_goal("create a grass field", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.grass")

    def test_planner_prefers_modular_building_recipe(self):
        result = plan_goal("blockout a simple modular building", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "architecture.modular_building")

    def test_planner_prefers_ground_points_recipe(self):
        result = plan_goal("create points on ground for layout", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.ground_points")

    def test_planner_prefers_scatter_intent_over_incidental_wall_keyword(self):
        result = plan_goal("scatter rocks along a wall", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.stones")

    def test_planner_prefers_scatter_intent_over_architecture_context(self):
        prompts = (
            "scatter stones around a building",
            "scatter rocks around a tower",
            "scatter rocks across a facade panel",
        )

        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = plan_goal(prompt, capabilities={})

                self.assertEqual(result["mode"], "recipe")
                self.assertEqual(result["recipe_id"], "scatter.stones")

    def test_planner_uses_word_boundaries_for_broad_keywords(self):
        result = plan_goal("towering grass field", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.grass")

    def test_planner_returns_unsupported_for_broad_request(self):
        result = plan_goal("make a photoreal cinematic character", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "unsupported")
        self.assertEqual(result["error"]["code"], "PLANNER_UNSUPPORTED_REQUEST")
        self.assertIn("retry_hint", result["error"])

    def test_planner_uses_semantic_graph_plan_for_heldout_prompt(self):
        result = plan_goal(
            "scatter uneven small pebbles across a sloped ground surface with random scale",
            capabilities={"node_types": {}},
        )

        self.assertEqual(result["mode"], "graph_plan")
        self.assertNotIn("recipe_id", result)
        self.assertIn("GeometryNodeDistributePointsOnFaces", result["node_types"])
        self.assertIn("GeometryNodeInstanceOnPoints", result["node_types"])
        self.assertTrue(result["validation"]["valid"])

    def test_planner_extracts_grid_tower_parameters(self):
        result = plan_goal("make a 12 level grid tower with 6 columns", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "architecture.grid_tower")
        self.assertEqual(result["parameters"], {"levels": 12, "columns": 6})
        self.assertTrue(
            any(
                operation["params"].get("client_id") == "grid_level_12"
                for operation in result["operations"]
                if operation["type"] == "geometry_nodes.create_node"
            )
        )

    def test_planner_extracts_scatter_parameters(self):
        result = plan_goal("scatter stones density 45 seed 9", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.stones")
        self.assertEqual(result["parameters"], {"density": 45, "seed": 9})

    def test_planner_extracts_grass_parameters(self):
        result = plan_goal("grass scatter density 100 scale 1.5", capabilities={})

        self.assertEqual(result["mode"], "recipe")
        self.assertEqual(result["recipe_id"], "scatter.grass")
        self.assertEqual(result["parameters"], {"density": 100, "scale": 1.5})

    def test_planner_rejects_recipe_when_capabilities_miss_required_node(self):
        result = plan_goal(
            "create a grass field",
            capabilities={
                "node_types": {
                    "GeometryNodeDistributePointsOnFaces": {},
                    "GeometryNodeRealizeInstances": {},
                }
            },
        )

        self.assertEqual(result["mode"], "unsupported")
        self.assertEqual(result["error"]["code"], "PLANNER_UNSUPPORTED_REQUEST")
        self.assertIn("GeometryNodeInstanceOnPoints", result["error"]["message"])
        self.assertEqual(result["error"]["details"]["missing_node_types"], ["GeometryNodeInstanceOnPoints"])


if __name__ == "__main__":
    unittest.main()
