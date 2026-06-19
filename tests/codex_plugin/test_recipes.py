import math
import unittest

from codex_plugin.blendex_mcp.recipes import REGISTRY, Recipe, RecipeParameter, RecipeRegistry
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


class RecipeTests(unittest.TestCase):
    def test_architecture_recipes_are_registered(self):
        recipe_ids = {recipe["recipe_id"] for recipe in REGISTRY.list_recipes()}

        self.assertIn("architecture.grid_tower", recipe_ids)
        self.assertIn("architecture.wall_panel", recipe_ids)
        self.assertIn("architecture.modular_building", recipe_ids)

    def test_scatter_recipes_are_registered(self):
        recipes_by_id = {recipe["recipe_id"]: recipe for recipe in REGISTRY.list_recipes()}

        self.assertEqual(recipes_by_id["scatter.stones"]["label"], "Random Stone Scatter")
        self.assertEqual(recipes_by_id["scatter.stones"]["category"], "scatter")
        self.assertEqual(
            recipes_by_id["scatter.stones"]["required_node_types"],
            [
                "GeometryNodeDistributePointsOnFaces",
                "GeometryNodeInstanceOnPoints",
                "GeometryNodeRealizeInstances",
            ],
        )
        self.assertEqual(
            recipes_by_id["scatter.stones"]["example_prompts"],
            ["Scatter random stones on the ground"],
        )
        self.assertEqual(recipes_by_id["scatter.ground_points"]["label"], "Ground Point Distribution")
        self.assertEqual(recipes_by_id["scatter.grass"]["label"], "Simple Grass Scatter")

    def test_scatter_recipes_reflect_parameters_in_labels(self):
        stone_operations = REGISTRY.build("scatter.stones", {"density": 37, "seed": 12})
        stone_labels = [operation["params"].get("label") for operation in stone_operations]

        self.assertIn("Stone Points density 37", stone_labels)
        self.assertIn("Stone Instances seed 12", stone_labels)

        ground_operations = REGISTRY.build("scatter.ground_points", {"density": 88, "seed": 34})
        ground_labels = [operation["params"].get("label") for operation in ground_operations]

        self.assertIn("Ground Points density 88", ground_labels)
        self.assertIn("Ground Random seed 34", ground_labels)

        grass_operations = REGISTRY.build("scatter.grass", {"density": 123, "scale": 2.5})
        grass_labels = [operation["params"].get("label") for operation in grass_operations]

        self.assertIn("Grass Points density 123", grass_labels)
        self.assertIn("Grass Instances scale 2.5", grass_labels)

    def test_scatter_recipe_parameters_validate_bounds_and_types(self):
        invalid_cases = [
            ("scatter.stones", {"density": 0}, "density must be >= 1"),
            ("scatter.stones", {"density": 201}, "density must be <= 200"),
            ("scatter.stones", {"seed": -1}, "seed must be >= 0"),
            ("scatter.stones", {"seed": 10000}, "seed must be <= 9999"),
            ("scatter.ground_points", {"density": 501}, "density must be <= 500"),
            ("scatter.grass", {"density": 1001}, "density must be <= 1000"),
            ("scatter.grass", {"scale": 0.09}, "scale must be >= 0.1"),
            ("scatter.grass", {"scale": 10.1}, "scale must be <= 10.0"),
            ("scatter.grass", {"density": 4.5}, "density must be an integer"),
            ("scatter.grass", {"scale": "large"}, "scale must be a number"),
        ]

        for recipe_id, params, message in invalid_cases:
            with self.subTest(recipe_id=recipe_id, params=params):
                with self.assertRaisesRegex(ValueError, message):
                    REGISTRY.build(recipe_id, params)

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

    def test_grid_tower_recipe_creates_level_modules(self):
        operations = REGISTRY.build("architecture.grid_tower", {"levels": 4, "columns": 3})
        created_client_ids = [
            operation["params"].get("client_id")
            for operation in operations
            if operation["type"] == "geometry_nodes.create_node"
        ]
        socket_values = [
            operation["params"]
            for operation in operations
            if operation["type"] == "geometry_nodes.set_socket_value"
        ]

        for level in range(1, 5):
            self.assertIn(f"grid_level_{level}", created_client_ids)
        self.assertIn(
            {"node_id": "grid_level_4", "socket": "Translation", "value": [0, 0, 3]},
            socket_values,
        )

    def test_wall_panel_recipe_creates_segment_modules(self):
        operations = REGISTRY.build("architecture.wall_panel", {"segments": 3})
        created_client_ids = [
            operation["params"].get("client_id")
            for operation in operations
            if operation["type"] == "geometry_nodes.create_node"
        ]

        self.assertIn("wall_segment_1", created_client_ids)
        self.assertIn("wall_segment_2", created_client_ids)
        self.assertIn("wall_segment_3", created_client_ids)

    def test_modular_building_recipe_creates_floor_modules(self):
        operations = REGISTRY.build("architecture.modular_building", {"floors": 3})
        created_client_ids = [
            operation["params"].get("client_id")
            for operation in operations
            if operation["type"] == "geometry_nodes.create_node"
        ]
        socket_values = [
            operation["params"]
            for operation in operations
            if operation["type"] == "geometry_nodes.set_socket_value"
        ]

        self.assertIn("building_floor_1", created_client_ids)
        self.assertIn("building_floor_2", created_client_ids)
        self.assertIn("building_floor_3", created_client_ids)
        self.assertIn(
            {"node_id": "building_floor_3", "socket": "Translation", "value": [0, 0, 2]},
            socket_values,
        )

    def test_registered_architecture_and_scatter_recipes_emit_valid_batches(self):
        recipes = [
            recipe for recipe in REGISTRY.list_recipes()
            if recipe["recipe_id"].startswith(("architecture.", "scatter."))
        ]

        self.assertTrue(recipes)
        for recipe in recipes:
            with self.subTest(recipe_id=recipe["recipe_id"]):
                operations = REGISTRY.build(recipe["recipe_id"])

                self.assertTrue(operations)
                operation_ids = [operation.get("id") for operation in operations]
                self.assertEqual(len(operation_ids), len(set(operation_ids)))

                created_nodes = [
                    operation for operation in operations
                    if operation.get("type") == "geometry_nodes.create_node"
                ]
                client_ids = [operation["params"].get("client_id") for operation in created_nodes]
                self.assertEqual(len(client_ids), len(set(client_ids)))

                node_types = {operation["params"].get("node_type") for operation in created_nodes}
                self.assertTrue(set(recipe["required_node_types"]).issubset(node_types))

                for operation in operations:
                    self.assertIsInstance(operation.get("id"), str)
                    self.assertTrue(operation["id"])
                    self.assertIsInstance(operation.get("type"), str)
                    self.assertTrue(operation["type"])
                    validate_request(OperationRequest.from_dict(operation))

    def test_registered_recipes_emit_complete_graph_batches(self):
        recipes = [
            recipe for recipe in REGISTRY.list_recipes()
            if recipe["recipe_id"].startswith(("architecture.", "scatter."))
        ]

        for recipe in recipes:
            with self.subTest(recipe_id=recipe["recipe_id"]):
                operations = REGISTRY.build(recipe["recipe_id"])
                operation_types = {operation["type"] for operation in operations}

                self.assertIn("scene.create_carrier_mesh", operation_types)
                self.assertIn("geometry_nodes.create_modifier", operation_types)
                self.assertIn("geometry_nodes.create_node", operation_types)
                self.assertIn("geometry_nodes.set_socket_value", operation_types)
                self.assertIn("geometry_nodes.link_sockets", operation_types)

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
