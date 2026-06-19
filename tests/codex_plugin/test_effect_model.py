import unittest

from codex_plugin.blendex_mcp.effect_model import parse_effect_intent


class EffectModelTests(unittest.TestCase):
    def test_parses_architecture_instance_and_deform_intent(self):
        intent = parse_effect_intent(
            "create a simple tower mass with repeating balconies that get smaller near the top"
        )

        self.assertEqual(intent["primary_effect"], "architecture")
        self.assertEqual(intent["unsupported_reasons"], [])
        self.assertIn("architecture", intent["effects"])
        self.assertIn("instance", intent["effects"])
        self.assertIn("deform", intent["effects"])
        self.assertIn("repetition", intent["constraints"])
        self.assertIn("scale variation", intent["constraints"])

    def test_parses_scatter_density_mask_intent(self):
        intent = parse_effect_intent(
            "scatter grass more densely near the center and sparsely near the edges"
        )

        self.assertEqual(intent["primary_effect"], "scatter")
        self.assertIn("scatter", intent["effects"])
        self.assertIn("field", intent["effects"])
        self.assertIn("selection", intent["effects"])
        self.assertIn("density gradient", intent["constraints"])

    def test_parses_material_selection_and_field_intent(self):
        intent = parse_effect_intent("assign a different material to upper faces based on height")

        self.assertEqual(intent["primary_effect"], "material")
        self.assertIn("material", intent["effects"])
        self.assertIn("selection", intent["effects"])
        self.assertIn("field", intent["effects"])
        self.assertIn("height based", intent["constraints"])

    def test_parses_attribute_capture_before_deform(self):
        intent = parse_effect_intent("capture the original position before deforming points upward")

        self.assertEqual(intent["primary_effect"], "attribute")
        self.assertIn("attribute", intent["effects"])
        self.assertIn("deform", intent["effects"])
        self.assertIn("field", intent["effects"])
        self.assertIn("capture before deformation", intent["constraints"])

    def test_extracts_numeric_parameters(self):
        intent = parse_effect_intent("make 12 floors with 6 columns and seed 9")

        self.assertEqual(intent["parameters"]["floors"], 12)
        self.assertEqual(intent["parameters"]["columns"], 6)
        self.assertEqual(intent["parameters"]["seed"], 9)

    def test_rejects_simulation_as_specific_unsupported_reason(self):
        intent = parse_effect_intent("make a fluid simulation with particles over 120 frames")

        self.assertEqual(intent["primary_effect"], "unsupported")
        self.assertIn("simulation_zones_out_of_scope", intent["unsupported_reasons"])
        self.assertIn("simulation", intent["effects"])

    def test_rejects_photoreal_character_as_specific_unsupported_reason(self):
        intent = parse_effect_intent("make a photoreal cinematic character with hair and skin")

        self.assertEqual(intent["primary_effect"], "unsupported")
        self.assertIn("photoreal_character_out_of_scope", intent["unsupported_reasons"])
        self.assertIn("character", intent["effects"])


if __name__ == "__main__":
    unittest.main()
