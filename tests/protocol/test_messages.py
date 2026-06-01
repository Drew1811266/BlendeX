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

    def test_success_response_round_trips_from_dict(self):
        payload = {
            "id": "req_3",
            "ok": True,
            "result": {"node_id": "Join Geometry"},
        }

        response = OperationResponse.from_dict(payload)

        self.assertTrue(response.ok)
        self.assertEqual(response.id, "req_3")
        self.assertEqual(response.result["node_id"], "Join Geometry")
        self.assertEqual(response.to_dict(), payload)

    def test_success_response_defaults_missing_result(self):
        response = OperationResponse.from_dict({"id": "req_4", "ok": True})

        self.assertEqual(response.result, {})
        self.assertEqual(response.to_dict(), {"id": "req_4", "ok": True, "result": {}})

    def test_error_response_round_trips_from_dict(self):
        payload = {
            "id": "req_5",
            "ok": False,
            "error": {"code": "VALIDATION_FAILED", "message": "Bad request."},
        }

        response = OperationResponse.from_dict(payload)

        self.assertFalse(response.ok)
        self.assertEqual(response.id, "req_5")
        self.assertEqual(response.error["code"], "VALIDATION_FAILED")
        self.assertEqual(response.to_dict(), payload)

    def test_rejects_response_with_non_bool_ok(self):
        with self.assertRaises(BlendexError) as raised:
            OperationResponse.from_dict({"id": "req_6", "ok": "true", "result": {}})

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")

    def test_rejects_failed_response_without_error(self):
        with self.assertRaises(BlendexError) as raised:
            OperationResponse.from_dict({"id": "req_7", "ok": False})

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")


if __name__ == "__main__":
    unittest.main()
