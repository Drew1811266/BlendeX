import unittest

from codex_plugin.blendex_mcp.blender_client import BlenderConnectionConfig


class BlenderClientTests(unittest.TestCase):
    def test_default_config_points_to_local_service(self):
        config = BlenderConnectionConfig()

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8765)
        self.assertEqual(config.timeout_seconds, 5.0)


if __name__ == "__main__":
    unittest.main()
