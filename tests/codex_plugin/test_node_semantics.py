import unittest

from codex_plugin.blendex_mcp.catalog import semantic_for_node
from codex_plugin.blendex_mcp.node_semantics import (
    CORE_NODE_TYPES,
    nodes_for_effect,
    semantic_record_for_node,
    validate_semantic_catalog,
    validate_semantic_record,
)


class NodeSemanticsTests(unittest.TestCase):
    def test_core_semantic_records_have_planner_ready_fields(self):
        required_fields = {
            "node_type",
            "role",
            "effects",
            "inputs",
            "outputs",
            "preconditions",
            "postconditions",
            "field_behavior",
            "instance_behavior",
            "pairings",
            "repair_hints",
        }

        self.assertGreaterEqual(len(CORE_NODE_TYPES), 20)
        for node_type in CORE_NODE_TYPES:
            with self.subTest(node_type=node_type):
                record = semantic_record_for_node(node_type)
                self.assertEqual(set(record) & required_fields, required_fields)
                self.assertEqual(record["node_type"], node_type)
                self.assertIsInstance(record["effects"], list)
                self.assertGreaterEqual(len(record["effects"]), 1)
                self.assertIsInstance(record["inputs"], dict)
                self.assertIsInstance(record["outputs"], dict)
                self.assertIsInstance(record["preconditions"], list)
                self.assertIsInstance(record["postconditions"], list)
                self.assertIsInstance(record["field_behavior"], dict)
                self.assertIsInstance(record["instance_behavior"], dict)
                self.assertIsInstance(record["pairings"], dict)
                self.assertIsInstance(record["repair_hints"], list)

    def test_validate_semantic_record_rejects_missing_required_fields(self):
        invalid = semantic_record_for_node("GeometryNodeJoinGeometry")
        invalid.pop("postconditions")

        with self.assertRaisesRegex(ValueError, "postconditions"):
            validate_semantic_record(invalid)

    def test_validate_semantic_catalog_accepts_core_catalog(self):
        result = validate_semantic_catalog()

        self.assertEqual(result["record_count"], len(CORE_NODE_TYPES))
        self.assertIn("GeometryNodeInstanceOnPoints", result["node_types"])

    def test_nodes_for_effect_returns_semantic_candidates(self):
        scatter_nodes = nodes_for_effect("scatter")
        instance_nodes = nodes_for_effect("instance")

        self.assertIn("GeometryNodeDistributePointsOnFaces", scatter_nodes)
        self.assertIn("GeometryNodeInstanceOnPoints", instance_nodes)

    def test_catalog_wrapper_preserves_legacy_semantic_shape(self):
        semantic = semantic_for_node("GeometryNodeJoinGeometry")

        self.assertIn("role", semantic)
        self.assertIn("typical_inputs", semantic)
        self.assertIn("typical_outputs", semantic)
        self.assertIn("planning_hints", semantic)
        self.assertIn("common_pairings", semantic)
        self.assertIn("effects", semantic)
        self.assertIn("postconditions", semantic)

    def test_semantic_lookups_return_independent_copies(self):
        first = semantic_record_for_node("GeometryNodeJoinGeometry")
        first["effects"].append("mutated")

        second = semantic_record_for_node("GeometryNodeJoinGeometry")

        self.assertNotIn("mutated", second["effects"])


if __name__ == "__main__":
    unittest.main()
