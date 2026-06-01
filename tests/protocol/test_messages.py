import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest, OperationResponse


class OperationMessageTests(unittest.TestCase):
    def test_request_round_trips_from_dict(self):
        payload = {
            "id": "req_1",
            "type": "geometry_nodes.create_node",
            "target": {"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            "params": {"node_type": "GeometryNodeJoinGeometry", "label": "Join"},
        }

        request = OperationRequest.from_dict(payload)

        self.assertEqual(request.id, "req_1")
        self.assertEqual(request.type, "geometry_nodes.create_node")
        self.assertEqual(request.target["object_id"], "Cube")
        self.assertEqual(request.to_dict(), payload)

    def test_error_response_shape(self):
        error = BlendexError(
            code="NODE_TYPE_NOT_FOUND",
            message="Node type is unavailable.",
            retry_hint="Refresh capabilities.",
        )

        response = OperationResponse.error("req_2", error)

        self.assertFalse(response.ok)
        self.assertEqual(response.id, "req_2")
        self.assertEqual(response.error["code"], "NODE_TYPE_NOT_FOUND")
        self.assertEqual(response.error["retry_hint"], "Refresh capabilities.")


if __name__ == "__main__":
    unittest.main()
