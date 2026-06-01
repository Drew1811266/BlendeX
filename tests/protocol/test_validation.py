import unittest

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


if __name__ == "__main__":
    unittest.main()
