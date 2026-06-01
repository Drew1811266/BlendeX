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


if __name__ == "__main__":
    unittest.main()
