import unittest

from blender_addon.blendex.logs import OperationLog
from blender_addon.blendex.state import BlendexState


class BlendexStateTests(unittest.TestCase):
    def test_records_recent_operations(self):
        state = BlendexState()
        state.record(OperationLog(request_id="req_1", operation="scene.inspect", ok=True, message="Scene inspected."))

        self.assertEqual(len(state.recent_logs), 1)
        self.assertEqual(state.recent_logs[0].operation, "scene.inspect")
        self.assertTrue(state.recent_logs[0].ok)

    def test_connection_fields_have_safe_defaults(self):
        state = BlendexState()

        self.assertFalse(state.service_running)
        self.assertFalse(state.client_connected)
        self.assertEqual(state.port, 8765)
        self.assertGreaterEqual(len(state.session_token), 16)


if __name__ == "__main__":
    unittest.main()
