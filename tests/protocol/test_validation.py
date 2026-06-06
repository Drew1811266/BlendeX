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

    def test_accepts_create_modifier_request(self):
        request = OperationRequest(
            id="req_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": "BlendeX Geometry"},
        )

        validate_request(request)

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
