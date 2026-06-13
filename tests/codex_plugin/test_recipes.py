import math
import unittest

from codex_plugin.blendex_mcp.recipes import REGISTRY, Recipe, RecipeParameter, RecipeRegistry


class RecipeTests(unittest.TestCase):
    def test_architecture_recipes_are_registered(self):
        recipe_ids = {recipe["recipe_id"] for recipe in REGISTRY.list_recipes()}

        self.assertIn("architecture.grid_tower", recipe_ids)
        self.assertIn("architecture.wall_panel", recipe_ids)
        self.assertIn("architecture.modular_building", recipe_ids)

    def test_grid_tower_recipe_builds_owned_graph_batch(self):
        operations = REGISTRY.build("architecture.grid_tower", {"levels": 4, "columns": 3})
        operation_types = [operation["type"] for operation in operations]

        self.assertEqual(operation_types[0], "scene.create_carrier_mesh")
        self.assertIn("geometry_nodes.create_modifier", operation_types)
        self.assertIn("geometry_nodes.create_node", operation_types)
        self.assertTrue(any(operation["params"].get("client_id") == "grid_join" for operation in operations))

    def test_grid_tower_recipe_reflects_parameters_and_validates_range(self):
        operations = REGISTRY.build("architecture.grid_tower", {"levels": 7, "columns": 2})
        labels = [operation["params"].get("label") for operation in operations]

        self.assertIn("Grid Tower 7x2", labels)
        with self.assertRaisesRegex(ValueError, "levels must be >= 1"):
            REGISTRY.build("architecture.grid_tower", {"levels": 0})

    def test_registry_lists_recipe_metadata(self):
        registry = RecipeRegistry()
        registry.register(
            Recipe(
                recipe_id="scatter.simple",
                label="Simple Scatter",
                category="scatter",
                parameters=[
                    RecipeParameter(
                        name="count",
                        value_type="integer",
                        default=12,
                        minimum=1,
                        maximum=100,
                        description="Number of instances.",
                    )
                ],
                builder=lambda params: [],
                required_node_types=["GeometryNodeInstanceOnPoints"],
                example_prompts=["Scatter pebbles on the ground"],
            )
        )

        self.assertEqual(
            registry.list_recipes(),
            [
                {
                    "recipe_id": "scatter.simple",
                    "label": "Simple Scatter",
                    "category": "scatter",
                    "parameters": [
                        {
                            "name": "count",
                            "value_type": "integer",
                            "default": 12,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Number of instances.",
                        }
                    ],
                    "required_node_types": ["GeometryNodeInstanceOnPoints"],
                    "example_prompts": ["Scatter pebbles on the ground"],
                }
            ],
        )

    def test_parameter_uses_default_and_validates_integer_range(self):
        parameter = RecipeParameter(
            name="count",
            value_type="integer",
            default=3,
            minimum=1,
            maximum=5,
            description="Count.",
        )

        self.assertEqual(parameter.normalize({}), 3)
        self.assertEqual(parameter.normalize({"count": 4}), 4)

        for value in (0, 6, True, 2.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parameter.normalize({"count": value})

    def test_unknown_recipe_errors(self):
        registry = RecipeRegistry()

        with self.assertRaisesRegex(ValueError, "Unknown recipe: missing"):
            registry.get("missing")
        with self.assertRaisesRegex(ValueError, "Unknown recipe: missing"):
            registry.build("missing", {})

    def test_registry_rejects_duplicate_recipe_ids(self):
        registry = RecipeRegistry()
        recipe = Recipe(
            recipe_id="scatter.simple",
            label="Simple Scatter",
            category="scatter",
            parameters=[],
            builder=lambda params: [],
            required_node_types=[],
            example_prompts=[],
        )
        duplicate = Recipe(
            recipe_id="scatter.simple",
            label="Different Scatter",
            category="scatter",
            parameters=[],
            builder=lambda params: [],
            required_node_types=[],
            example_prompts=[],
        )

        registry.register(recipe)

        with self.assertRaisesRegex(ValueError, "Duplicate recipe id: scatter.simple"):
            registry.register(duplicate)
        self.assertEqual(registry.get("scatter.simple").label, "Simple Scatter")

    def test_number_and_string_validation_protects_recipe_params(self):
        density = RecipeParameter("density", "number", 0.5, 0.0, 1.0, "Density.")
        label = RecipeParameter("label", "string", "Oak", description="Label.")

        self.assertEqual(density.normalize({"density": 0.75}), 0.75)
        self.assertEqual(density.normalize({"density": 1}), 1)
        self.assertEqual(label.normalize({"label": "Birch"}), "Birch")

        for value in (True, "0.5", math.inf, math.nan, -0.1, 1.1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    density.normalize({"density": value})

        for value in ("", "   ", 3):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    label.normalize({"label": value})

    def test_build_uses_normalized_params(self):
        seen_params = []

        def build_operations(params):
            seen_params.append(params)
            return [
                {
                    "id": "op_1",
                    "type": "geometry_nodes.set_socket_value",
                    "target": {},
                    "params": {"value": params["density"], "label": params["label"]},
                }
            ]

        recipe = Recipe(
            recipe_id="material.leaf",
            label="Leaf Material",
            category="materials",
            parameters=[
                RecipeParameter("density", "number", 0.5, 0.0, 1.0, "Density."),
                RecipeParameter("label", "string", "Oak", description="Label."),
            ],
            builder=build_operations,
            required_node_types=[],
            example_prompts=[],
        )

        operations = recipe.build({"label": "Birch"})

        self.assertEqual(seen_params, [{"density": 0.5, "label": "Birch"}])
        self.assertEqual(operations[0]["params"], {"value": 0.5, "label": "Birch"})


if __name__ == "__main__":
    unittest.main()
