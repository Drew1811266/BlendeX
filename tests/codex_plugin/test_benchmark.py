import pathlib
import unittest

from codex_plugin.blendex_mcp.benchmark import run_heldout_benchmark


ROOT = pathlib.Path(__file__).resolve().parents[2]


class BenchmarkTests(unittest.TestCase):
    def test_fake_runtime_benchmark_plans_all_heldout_prompts_without_recipes(self):
        summary = run_heldout_benchmark()

        self.assertEqual(summary["version"], "0.5")
        self.assertGreaterEqual(summary["total"], 20)
        self.assertEqual(summary["graph_plan_count"], summary["total"])
        self.assertEqual(summary["valid_plan_count"], summary["total"])
        self.assertEqual(summary["recipe_count"], 0)
        self.assertEqual(summary["unsupported_count"], 0)
        for result in summary["results"]:
            with self.subTest(prompt=result["id"]):
                self.assertEqual(result["mode"], "graph_plan")
                self.assertTrue(result["valid"])
                self.assertFalse(result["used_recipe"])
                self.assertNotIn("recipe_id", result)
                self.assertGreaterEqual(result["node_count"], 2)

    def test_benchmark_summarizes_effect_category_results(self):
        summary = run_heldout_benchmark()

        for effect in {
            "architecture",
            "scatter",
            "instance",
            "deform",
            "field",
            "attribute",
            "material",
            "selection",
        }:
            with self.subTest(effect=effect):
                effect_summary = summary["by_effect"][effect]
                self.assertGreaterEqual(effect_summary["total"], 1)
                self.assertEqual(effect_summary["valid"], effect_summary["total"])
                self.assertIn("property_pass", effect_summary)

    def test_benchmark_reports_minimum_property_details_per_prompt(self):
        summary = run_heldout_benchmark(limit=3)

        self.assertEqual(summary["total"], 3)
        for result in summary["results"]:
            with self.subTest(prompt=result["id"]):
                self.assertIn("minimum_nodes", result)
                self.assertIn("meets_minimum_nodes", result)
                self.assertIn("expected_effects", result)
                self.assertIn("observed_effects", result)
                self.assertIn("missing_effects", result)
                self.assertIsInstance(result["missing_effects"], list)

    def test_smoke_script_has_optional_generated_graph_mode(self):
        smoke = (ROOT / "tests" / "integration" / "blender_smoke.py").read_text(encoding="utf-8")
        launcher = (ROOT / "scripts" / "run_blender_smoke.py").read_text(encoding="utf-8")

        self.assertIn("BLENDEX_GENERATED_GRAPH_SMOKE", smoke)
        self.assertIn("run_generated_graph_smoke", smoke)
        self.assertIn("plan_graph", smoke)
        self.assertIn("BLENDEX_GENERATED_GRAPH_SMOKE", launcher)


if __name__ == "__main__":
    unittest.main()
