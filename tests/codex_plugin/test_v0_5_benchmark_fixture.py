import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/benchmarks/v0-5-heldout-prompts.json"


class V05BenchmarkFixtureTest(unittest.TestCase):
    def test_fixture_contains_heldout_prompts_without_recipe_answers(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], "0.5")
        prompts = data["prompts"]
        self.assertGreaterEqual(len(prompts), 20)
        recipe_prefixes = ("architecture.", "scatter.")
        for item in prompts:
            with self.subTest(prompt=item.get("id")):
                self.assertIsInstance(item["prompt"], str)
                self.assertGreaterEqual(len(item["expected_effects"]), 1)
                self.assertNotIn("recipe_id", item)
                self.assertFalse(item["id"].startswith(recipe_prefixes))
                self.assertIn("minimum_nodes", item)
                self.assertGreaterEqual(item["minimum_nodes"], 3)

    def test_fixture_covers_core_reasoning_domains(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        effects = {effect for item in data["prompts"] for effect in item["expected_effects"]}
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
                self.assertIn(effect, effects)


if __name__ == "__main__":
    unittest.main()
