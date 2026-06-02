import unittest

from blender_addon.blendex.server import dispatch_payload


class DispatchTests(unittest.TestCase):
    def test_dispatch_rejects_unknown_operation_as_json_response(self):
        response = dispatch_payload(
            {
                "id": "req_bad",
                "type": "python.exec",
                "target": {},
                "params": {"code": "print('blocked')"},
            },
            executor=None,
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "UNSUPPORTED_OPERATION")


if __name__ == "__main__":
    unittest.main()
