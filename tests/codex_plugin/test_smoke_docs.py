import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class SmokeAndDemoDocsTests(unittest.TestCase):
    def test_blender_smoke_executes_architecture_and_scatter_recipes(self):
        smoke = (ROOT / "tests" / "integration" / "blender_smoke.py").read_text()

        self.assertIn("REGISTRY.build", smoke)
        self.assertIn("architecture.grid_tower", smoke)
        self.assertIn("scatter.ground_points", smoke)
        self.assertIn("undo_last_batch", smoke)
        self.assertIn("traceback.print_exc", smoke)
        self.assertIn("raise SystemExit(1)", smoke)

    def test_demo_prompts_cover_all_builtin_recipes_and_flow(self):
        demo = (ROOT / "docs" / "demo-prompts.md").read_text()

        for recipe_id in (
            "architecture.grid_tower",
            "architecture.wall_panel",
            "architecture.modular_building",
            "scatter.stones",
            "scatter.ground_points",
            "scatter.grass",
        ):
            self.assertIn(recipe_id, demo)
        for required_term in ("dry-run", "confirm", "inspect", "undo"):
            self.assertIn(required_term, demo.lower())


if __name__ == "__main__":
    unittest.main()
