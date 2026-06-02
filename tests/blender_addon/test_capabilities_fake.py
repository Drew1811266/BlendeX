import unittest

from blender_addon.blendex.capabilities import scan_capabilities


class FakeBlender:
    version = (4, 1, 0)
    node_types = {
        "GeometryNodeJoinGeometry": {"inputs": ["Geometry"], "outputs": ["Geometry"]},
        "GeometryNodeInstanceOnPoints": {"inputs": ["Points", "Instance"], "outputs": ["Instances"]},
    }


class CapabilityTests(unittest.TestCase):
    def test_scan_returns_version_and_node_types(self):
        result = scan_capabilities(FakeBlender())

        self.assertEqual(result["blender_version"], [4, 1, 0])
        self.assertIn("GeometryNodeJoinGeometry", result["node_types"])
        self.assertEqual(result["supported_operations"][0], "capabilities.scan")


if __name__ == "__main__":
    unittest.main()
