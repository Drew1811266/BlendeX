import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from blendex_protocol.errors import BlendexError

from blender_addon.blendex.safety import dry_run_operations, validate_operations
from blender_addon.blendex.executor import GeometryNodesExecutor
from tests.blender_addon.test_executor_fake import FakeBlenderNodeCollection, FakeContext


class RecordingExecutor:
    def __init__(self, failing_type=None):
        self.failing_type = failing_type
        self.validated = []

    def validate(self, request):
        self.validated.append(request.type)
        if request.type == self.failing_type:
            raise BlendexError("SOCKET_NOT_FOUND", "Socket missing.", retry_hint="Inspect the tree first.")
        return {"validated": True}


class LinkRejectingExecutor(RecordingExecutor):
    def validate(self, request):
        if request.type == "geometry_nodes.link_sockets":
            raise BlendexError("NODE_TYPE_NOT_FOUND", "Node not found: join_1")
        return super().validate(request)


class ModifierAwareExecutor(RecordingExecutor):
    def __init__(self, existing_modifiers=None, node_types=None):
        super().__init__()
        self.existing_modifiers = set(existing_modifiers or [])
        self.node_types = set(node_types or {"GeometryNodeJoinGeometry"})

    def validate(self, request):
        self.validated.append(request.type)
        if request.type == "geometry_nodes.create_node":
            node_type = request.params["node_type"]
            if node_type not in self.node_types:
                raise BlendexError("NODE_TYPE_NOT_FOUND", f"Node type is unavailable: {node_type}")
            modifier_id = request.target.get("modifier_id", "BlendeX Geometry")
            if (request.target["object_id"], modifier_id) not in self.existing_modifiers:
                raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier not found: {modifier_id}")
        return {"validated": True}


class SafetyTests(unittest.TestCase):
    def test_validate_operations_returns_valid_status(self):
        result = validate_operations(
            [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}],
            RecordingExecutor(),
        )

        self.assertEqual(result["status"], "valid")
        self.assertTrue(result["operations"][0]["ok"])
        self.assertEqual(result["operations"][0]["message"], "OK")

    def test_validate_operations_returns_invalid_entry(self):
        result = validate_operations(
            [
                {
                    "id": "op_bad",
                    "type": "geometry_nodes.set_socket_value",
                    "target": {"object_id": "Cube"},
                    "params": {"node_id": "Value", "socket": "Missing", "value": 1.0},
                }
            ],
            RecordingExecutor(failing_type="geometry_nodes.set_socket_value"),
        )

        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["operations"][0]["ok"])
        self.assertEqual(result["operations"][0]["error"]["code"], "SOCKET_NOT_FOUND")
        self.assertEqual(result["operations"][0]["error"]["retry_hint"], "Inspect the tree first.")

    def test_validate_operations_returns_partial_for_mixed_results(self):
        result = validate_operations(
            [
                {"id": "op_ok", "type": "scene.inspect", "target": {}, "params": {}},
                {
                    "id": "op_bad",
                    "type": "geometry_nodes.set_socket_value",
                    "target": {"object_id": "Cube"},
                    "params": {"node_id": "Value", "socket": "Missing", "value": 1.0},
                },
            ],
            RecordingExecutor(failing_type="geometry_nodes.set_socket_value"),
        )

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["operations"][0]["ok"])
        self.assertFalse(result["operations"][1]["ok"])

    def test_dry_run_returns_preview_sections_and_simulates_client_ids(self):
        result = dry_run_operations(
            [
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "client_id": "join_1"},
                },
                {
                    "id": "op_link",
                    "type": "geometry_nodes.link_sockets",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {
                        "from_node": "Group Input",
                        "from_socket": "Geometry",
                        "to_node": "join_1",
                        "to_socket": "Geometry",
                    },
                },
            ],
            LinkRejectingExecutor(),
        )

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["operations"][1]["ok"])
        self.assertEqual(result["preview"]["nodes"][0]["client_id"], "join_1")
        self.assertEqual(result["preview"]["links"][0]["to_node"], "join_1")
        self.assertEqual(result["warnings"][0]["code"], "SIMULATED_NODE_METADATA")
        self.assertEqual(result["preview"]["warnings"][0]["code"], "SIMULATED_NODE_METADATA")

    def test_dry_run_ignores_non_string_node_reference_params(self):
        result = dry_run_operations(
            [{"id": "op_scene", "type": "scene.inspect", "target": {}, "params": {"node_id": []}}],
            RecordingExecutor(),
        )

        self.assertEqual(result["status"], "valid")
        self.assertTrue(result["operations"][0]["ok"])

    def test_validate_operations_rejects_protocol_allowed_but_unimplemented_operation(self):
        result = validate_operations(
            [{"id": "op_unimplemented", "type": "scene.list_modifiers", "target": {}, "params": {}}],
            RecordingExecutor(),
        )

        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["operations"][0]["ok"])
        self.assertEqual(result["operations"][0]["error"]["code"], "UNSUPPORTED_OPERATION")

    def test_dry_run_rejects_protocol_allowed_but_unimplemented_operation(self):
        result = dry_run_operations(
            [{"id": "op_unimplemented", "type": "scene.list_modifiers", "target": {}, "params": {}}],
            RecordingExecutor(),
        )

        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["operations"][0]["ok"])
        self.assertEqual(result["operations"][0]["error"]["code"], "UNSUPPORTED_OPERATION")

    def test_dry_run_does_not_swallow_simulated_source_node_errors(self):
        result = dry_run_operations(
            [
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "client_id": "join_1"},
                },
                {
                    "id": "op_link",
                    "type": "geometry_nodes.link_sockets",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {
                        "from_node": "join_1",
                        "from_socket": "Geometry",
                        "to_node": "Group Output",
                        "to_socket": "Missing",
                    },
                },
            ],
            LinkRejectingExecutor(),
        )

        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][1]["error"]["code"], "NODE_TYPE_NOT_FOUND")

    def test_dry_run_does_not_swallow_real_source_socket_error_for_simulated_target_node(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)

        result = dry_run_operations(
            [
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "client_id": "join_1"},
                },
                {
                    "id": "op_link",
                    "type": "geometry_nodes.link_sockets",
                    "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                    "params": {
                        "from_node": source.name,
                        "from_socket": "Missing",
                        "to_node": "join_1",
                        "to_socket": "Geometry",
                    },
                },
            ],
            executor,
        )

        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][1]["error"]["code"], "SOCKET_NOT_FOUND")

    def test_dry_run_simulates_modifier_created_earlier_in_batch(self):
        result = dry_run_operations(
            [
                {
                    "id": "op_modifier",
                    "type": "geometry_nodes.create_modifier",
                    "target": {"object_id": "Cube"},
                    "params": {"modifier_id": "Generated Geometry"},
                },
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "Generated Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "client_id": "join_1"},
                },
            ],
            ModifierAwareExecutor(),
        )

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["operations"][1]["ok"])
        self.assertEqual(result["preview"]["modifiers"][0]["modifier_id"], "Generated Geometry")
        self.assertEqual(result["preview"]["nodes"][0]["client_id"], "join_1")
        self.assertEqual(result["warnings"][0]["code"], "SIMULATED_MODIFIER")

    def test_validate_operations_simulates_modifier_created_earlier_in_batch(self):
        result = validate_operations(
            [
                {
                    "id": "op_modifier",
                    "type": "geometry_nodes.create_modifier",
                    "target": {"object_id": "Cube"},
                    "params": {"modifier_id": "Generated Geometry"},
                },
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "Generated Geometry"},
                    "params": {"node_type": "GeometryNodeJoinGeometry", "client_id": "join_1"},
                },
            ],
            ModifierAwareExecutor(),
        )

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["operations"][1]["ok"])
        self.assertEqual(result["warnings"][0]["code"], "SIMULATED_MODIFIER")

    def test_dry_run_simulated_modifier_keeps_unavailable_node_type_invalid(self):
        result = dry_run_operations(
            [
                {
                    "id": "op_modifier",
                    "type": "geometry_nodes.create_modifier",
                    "target": {"object_id": "Cube"},
                    "params": {"modifier_id": "Generated Geometry"},
                },
                {
                    "id": "op_node",
                    "type": "geometry_nodes.create_node",
                    "target": {"object_id": "Cube", "modifier_id": "Generated Geometry"},
                    "params": {"node_type": "ShaderNodeValue", "client_id": "value_1"},
                },
            ],
            ModifierAwareExecutor(),
        )

        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][1]["error"]["code"], "NODE_TYPE_NOT_FOUND")
        self.assertEqual(result["preview"]["nodes"], [])


if __name__ == "__main__":
    unittest.main()
