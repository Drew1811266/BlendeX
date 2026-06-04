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
                "geometry_nodes.create_modifier",
                "geometry_nodes.create_node",
                "geometry_nodes.inspect_tree",
                "geometry_nodes.label_node",
                "geometry_nodes.link_sockets",
                "geometry_nodes.mark_ownership",
                "geometry_nodes.set_socket_value",
                "safety.dry_run",
                "safety.validate_batch",
                "scene.create_carrier_mesh",
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
        node = result["node_types"]["GeometryNodeJoinGeometry"]
        self.assertEqual(node["inputs"], [])
        self.assertEqual(node["outputs"], [])
        self.assertFalse(node["metadata_complete"])
        self.assertNotIn("ShaderNodeBsdfPrincipled", result["node_types"])

    def test_scan_merges_semantic_catalog_for_available_nodes_only(self):
        class Runtime:
            version = (4, 3, 0)
            node_types = {
                "GeometryNodeJoinGeometry": {"inputs": [], "outputs": [], "metadata_complete": False}
            }

        result = scan_capabilities(Runtime())

        self.assertIn("semantic", result["node_types"]["GeometryNodeJoinGeometry"])
        self.assertNotIn("GeometryNodeRealizeInstances", result["node_types"])

    def test_scan_bpy_capabilities_reads_template_sockets_when_available(self):
        class FakeSocketTemplate:
            def __init__(self, name, identifier, bl_socket_idname):
                self.name = name
                self.identifier = identifier
                self.bl_socket_idname = bl_socket_idname

        class GeometryNodeJoinGeometry:
            @classmethod
            def input_template(cls, index):
                if index == 0:
                    return FakeSocketTemplate("Geometry", "Geometry", "NodeSocketGeometry")
                raise RuntimeError("end")

            @classmethod
            def output_template(cls, index):
                if index == 0:
                    return FakeSocketTemplate("Geometry", "Geometry", "NodeSocketGeometry")
                raise RuntimeError("end")

        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return [GeometryNodeJoinGeometry]

        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(4, 3, 0)),
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

        node = result["node_types"]["GeometryNodeJoinGeometry"]
        self.assertTrue(node["metadata_complete"])
        self.assertEqual(node["inputs"][0]["name"], "Geometry")
        self.assertEqual(node["outputs"][0]["socket_type"], "NodeSocketGeometry")


if __name__ == "__main__":
    unittest.main()
