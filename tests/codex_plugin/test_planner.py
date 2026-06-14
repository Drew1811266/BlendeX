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

    def test_planner_returns_unsupported_for_broad_request(self):
        result = plan_goal("make a photoreal cinematic character", capabilities={"node_types": {}})

        self.assertEqual(result["mode"], "unsupported")
        self.assertEqual(result["error"]["code"], "PLANNER_UNSUPPORTED_REQUEST")
        self.assertIn("retry_hint", result["error"])


if __name__ == "__main__":
    unittest.main()
