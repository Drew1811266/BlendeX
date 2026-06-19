from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/superpowers/specs/2026-06-19-blendex-v0-5-geometry-nodes-reasoning-design.md"
PLAN = ROOT / "docs/superpowers/plans/2026-06-19-blendex-v0-5-geometry-nodes-reasoning.md"


class V05DocsTest(unittest.TestCase):
    def test_design_spec_defines_reasoning_and_anti_template_bar(self):
        text = SPEC.read_text(encoding="utf-8")
        required_phrases = [
            "Geometry Nodes reasoning system",
            'not "more templates"',
            "Anti-Template Requirement",
            "held-out prompts",
            "fields",
            "attributes",
            "instances",
            "repair",
            "v0.50: Readiness Audit",
        ]
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_plan_splits_v0_5_into_ten_version_slices(self):
        text = PLAN.read_text(encoding="utf-8")
        for patch in range(41, 51):
            with self.subTest(patch=patch):
                self.assertIn(f"v0.{patch}", text)
        self.assertIn("Backward graph planner", text)
        self.assertIn("Runtime validation and repair loop", text)


if __name__ == "__main__":
    unittest.main()
