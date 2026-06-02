import sys
import types
import unittest

from blender_addon.blendex.capabilities import scan_bpy_capabilities, scan_capabilities


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
        self.assertEqual(
            result["supported_operations"],
            [
                "capabilities.scan",
                "capabilities.supported_operations",
                "geometry_nodes.create_node",
                "geometry_nodes.inspect_tree",
                "scene.inspect",
            ],
        )

    def test_scan_bpy_capabilities_filters_geometry_node_subclasses(self):
        class GeometryNodeJoinGeometry:
            pass

        class ShaderNodeBsdfPrincipled:
            pass

        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return [GeometryNodeJoinGeometry, ShaderNodeBsdfPrincipled]

        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(4, 2, 0)),
            types=types.SimpleNamespace(GeometryNode=GeometryNode),
        )

        previous_bpy = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            result = scan_bpy_capabilities()
        finally:
            if previous_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = previous_bpy

        self.assertEqual(result["blender_version"], [4, 2, 0])
        self.assertEqual(
            result["node_types"]["GeometryNodeJoinGeometry"],
            {"inputs": [], "outputs": []},
        )
        self.assertNotIn("ShaderNodeBsdfPrincipled", result["node_types"])


if __name__ == "__main__":
    unittest.main()
