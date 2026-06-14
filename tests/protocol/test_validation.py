import pathlib
import sys
import unittest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


class ValidationTests(unittest.TestCase):
    def test_rejects_unknown_operation(self):
        request = OperationRequest(
            id="req_bad",
            type="python.exec",
            target={},
            params={"code": "print('blocked')"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "UNSUPPORTED_OPERATION")

    def test_accepts_create_node_request(self):
        request = OperationRequest(
            id="req_ok",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry"},
        )

        validate_request(request)

    def test_rejects_missing_geometry_nodes_object_id(self):
        request = OperationRequest(
            id="req_missing_object",
            type="geometry_nodes.inspect_tree",
            target={},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_invalid_geometry_nodes_object_id(self):
        for object_id in ("", 123):
            with self.subTest(object_id=object_id):
                request = OperationRequest(
                    id="req_invalid_object",
                    type="geometry_nodes.inspect_tree",
                    target={"object_id": object_id},
                    params={},
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_missing_create_node_type(self):
        request = OperationRequest(
            id="req_missing_node_type",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube"},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_invalid_create_node_type(self):
        for node_type in ("", 123):
            with self.subTest(node_type=node_type):
                request = OperationRequest(
                    id="req_invalid_node_type",
                    type="geometry_nodes.create_node",
                    target={"object_id": "Cube"},
                    params={"node_type": node_type},
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_create_node_invalid_location(self):
        request = OperationRequest(
            id="req_bad_location",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube"},
            params={"node_type": "GeometryNodeJoinGeometry", "location": "not-a-location"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_create_node_non_string_label(self):
        request = OperationRequest(
            id="req_bad_label",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube"},
            params={"node_type": "GeometryNodeJoinGeometry", "label": 123},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_create_modifier_request(self):
        request = OperationRequest(
            id="req_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": "BlendeX Geometry"},
        )

        validate_request(request)

    def test_rejects_create_modifier_empty_modifier_id(self):
        request = OperationRequest(
            id="req_bad_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": ""},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_create_carrier_mesh_non_string_name(self):
        request = OperationRequest(
            id="req_carrier_bad",
            type="scene.create_carrier_mesh",
            target={},
            params={"name": 123},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_link_sockets_request(self):
        request = OperationRequest(
            id="req_link",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": "Group Input",
                "from_socket": "Geometry",
                "to_node": "Group Output",
                "to_socket": "Geometry",
            },
        )

        validate_request(request)

    def test_rejects_link_sockets_missing_endpoint(self):
        request = OperationRequest(
            id="req_link_bad",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube"},
            params={"from_node": "A", "from_socket": "Geometry", "to_node": "B"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_set_socket_value_request(self):
        request = OperationRequest(
            id="req_value",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_id": "Value", "socket": "Value", "value": 2.5},
        )

        validate_request(request)

    def test_rejects_set_socket_value_missing_value_key(self):
        request = OperationRequest(
            id="req_value_bad",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube"},
            params={"node_id": "Value", "socket": "Value"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_set_socket_value_nested_non_finite_values(self):
        invalid_values = [
            [float("nan")],
            {"x": float("inf")},
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                request = OperationRequest(
                    id="req_value_bad",
                    type="geometry_nodes.set_socket_value",
                    target={"object_id": "Cube"},
                    params={"node_id": "Value", "socket": "Value", "value": value},
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_set_socket_value_nested_huge_integer(self):
        request = OperationRequest(
            id="req_value_bad",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube"},
            params={"node_id": "Value", "socket": "Value", "value": [10**1000]},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_batch_validation_request(self):
        request = OperationRequest(
            id="req_batch",
            type="safety.validate_batch",
            target={},
            params={
                "operations": [
                    {
                        "id": "op_1",
                        "type": "scene.inspect",
                        "target": {},
                        "params": {},
                    }
                ]
            },
        )

        validate_request(request)

    def test_accepts_confirmed_execute_batch_request(self):
        request = OperationRequest(
            id="req_batch",
            type="safety.execute_batch",
            target={"object_id": "Cube"},
            params={
                "confirmed": True,
                "confirmation_id": "confirm_1",
                "summary": "Create a small node graph",
                "operations": [
                    {
                        "id": "op_1",
                        "type": "geometry_nodes.create_modifier",
                        "target": {"object_id": "Cube"},
                        "params": {"modifier_id": "BlendeX Geometry"},
                    }
                ],
            },
        )

        validate_request(request)

    def test_rejects_execute_batch_without_confirmed_true(self):
        base_params = {
            "confirmation_id": "confirm_1",
            "summary": "Inspect scene",
            "operations": [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}],
        }

        for params in (
            base_params,
            {**base_params, "confirmed": False},
        ):
            with self.subTest(params=params):
                request = OperationRequest(
                    id="req_batch",
                    type="safety.execute_batch",
                    target={},
                    params=params,
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
                self.assertIn("dry-run", raised.exception.retry_hint)

    def test_rejects_execute_batch_missing_or_empty_confirmation_id(self):
        base_params = {
            "confirmed": True,
            "summary": "Inspect scene",
            "operations": [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}],
        }

        for params in (
            base_params,
            {**base_params, "confirmation_id": ""},
        ):
            with self.subTest(params=params):
                request = OperationRequest(
                    id="req_batch",
                    type="safety.execute_batch",
                    target={},
                    params=params,
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
                self.assertIn("confirmation_id", raised.exception.retry_hint)

    def test_rejects_execute_batch_missing_or_empty_summary(self):
        base_params = {
            "confirmed": True,
            "confirmation_id": "confirm_1",
            "operations": [{"id": "op_1", "type": "scene.inspect", "target": {}, "params": {}}],
        }

        for params in (
            base_params,
            {**base_params, "summary": ""},
        ):
            with self.subTest(params=params):
                request = OperationRequest(
                    id="req_batch",
                    type="safety.execute_batch",
                    target={},
                    params=params,
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
                self.assertIn("summary", raised.exception.retry_hint)

    def test_rejects_inspect_batch_without_batch_id(self):
        request = OperationRequest(
            id="req_batch_inspect",
            type="safety.inspect_batch",
            target={},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_batch_history_with_positive_integer_limit(self):
        request = OperationRequest(
            id="req_batch_history",
            type="safety.batch_history",
            target={},
            params={"limit": 3},
        )

        validate_request(request)

    def test_rejects_batch_history_with_invalid_limit(self):
        for limit in (0, -1, 2.5, True):
            with self.subTest(limit=limit):
                request = OperationRequest(
                    id="req_batch_history_bad",
                    type="safety.batch_history",
                    target={},
                    params={"limit": limit},
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_accepts_undo_last_batch_without_params(self):
        request = OperationRequest(
            id="req_undo",
            type="safety.undo_last_batch",
            target={},
            params={},
        )

        validate_request(request)

    def test_rejects_undo_last_batch_with_unexpected_params(self):
        request = OperationRequest(
            id="req_undo_bad",
            type="safety.undo_last_batch",
            target={},
            params={"operations": []},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_batch_validation_without_operations_array(self):
        request = OperationRequest(
            id="req_batch_bad",
            type="safety.validate_batch",
            target={},
            params={"operations": "not a list"},
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_batch_validation_or_dry_run_with_empty_operations_array(self):
        for operation_type in ("safety.validate_batch", "safety.dry_run"):
            with self.subTest(operation_type=operation_type):
                request = OperationRequest(
                    id="req_batch_empty",
                    type=operation_type,
                    target={},
                    params={"operations": []},
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_confirmed_execute_batch_with_empty_operations_array(self):
        request = OperationRequest(
            id="req_batch_empty",
            type="safety.execute_batch",
            target={},
            params={
                "confirmed": True,
                "confirmation_id": "confirm_1",
                "summary": "Inspect scene",
                "operations": [],
            },
        )

        with self.assertRaises(BlendexError) as raised:
            validate_request(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_batch_operation_nested_invalid_json_values(self):
        invalid_operations = [
            {
                "id": "op_1",
                "type": "geometry_nodes.set_socket_value",
                "target": {"object_id": "Cube"},
                "params": {"value": [float("nan")]},
            },
            {
                "id": "op_2",
                "type": "geometry_nodes.inspect_tree",
                "target": {"object_id": "Cube", "x": [10**1000]},
                "params": {},
            },
        ]

        for operation in invalid_operations:
            with self.subTest(operation=operation):
                request = OperationRequest(
                    id="req_batch_bad",
                    type="safety.validate_batch",
                    target={},
                    params={"operations": [operation]},
                )

                with self.assertRaises(BlendexError) as raised:
                    validate_request(request)

                self.assertEqual(raised.exception.code, "VALIDATION_FAILED")


if __name__ == "__main__":
    unittest.main()
