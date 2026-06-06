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
    def _scan_with_fake_bpy(self, fake_bpy):
        previous_bpy = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            return scan_bpy_capabilities()
        finally:
            if previous_bpy is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = previous_bpy

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

    def test_scan_does_not_advertise_unimplemented_future_operations(self):
        result = scan_capabilities(FakeBlender())

        self.assertNotIn("geometry_nodes.link_sockets", result["supported_operations"])
        self.assertNotIn("geometry_nodes.set_socket_value", result["supported_operations"])
        self.assertNotIn("safety.dry_run", result["supported_operations"])

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

        result = self._scan_with_fake_bpy(fake_bpy)

        self.assertEqual(result["blender_version"], [4, 2, 0])
        node = result["node_types"]["GeometryNodeJoinGeometry"]
        self.assertEqual(node["inputs"], [])
        self.assertEqual(node["outputs"], [])
        self.assertFalse(node["metadata_complete"])
        self.assertNotIn("ShaderNodeBsdfPrincipled", result["node_types"])

    def test_scan_bpy_capabilities_discovers_function_shader_and_group_nodes(self):
        class GeometryNodeJoinGeometry:
            pass

        class FunctionNodeRandomValue:
            pass

        class ShaderNodeMath:
            pass

        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return [GeometryNodeJoinGeometry]

        class FunctionNode:
            @classmethod
            def __subclasses__(cls):
                return [FunctionNodeRandomValue]

        class ShaderNode:
            @classmethod
            def __subclasses__(cls):
                return [ShaderNodeMath, GeometryNodeJoinGeometry]

        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(4, 3, 0)),
            types=types.SimpleNamespace(
                GeometryNode=GeometryNode,
                FunctionNode=FunctionNode,
                ShaderNode=ShaderNode,
                NodeGroupInput=type("NodeGroupInput", (), {}),
                NodeGroupOutput=type("NodeGroupOutput", (), {}),
            ),
        )

        result = self._scan_with_fake_bpy(fake_bpy)

        self.assertEqual(
            set(result["node_types"]),
            {
                "FunctionNodeRandomValue",
                "GeometryNodeJoinGeometry",
                "NodeGroupInput",
                "NodeGroupOutput",
                "ShaderNodeMath",
            },
        )
        self.assertIn("semantic", result["node_types"]["FunctionNodeRandomValue"])
        self.assertIn("semantic", result["node_types"]["ShaderNodeMath"])
        self.assertIn("semantic", result["node_types"]["NodeGroupInput"])

    def test_scan_merges_semantic_catalog_for_available_nodes_only(self):
        class Runtime:
            version = (4, 3, 0)
            node_types = {
                "GeometryNodeJoinGeometry": {"inputs": [], "outputs": [], "metadata_complete": False}
            }

        result = scan_capabilities(Runtime())

        self.assertIn("semantic", result["node_types"]["GeometryNodeJoinGeometry"])
        self.assertNotIn("GeometryNodeRealizeInstances", result["node_types"])

    def test_scan_returns_independent_semantic_metadata(self):
        first = scan_capabilities(FakeBlender())
        first["node_types"]["GeometryNodeJoinGeometry"]["semantic"]["typical_inputs"].append("MUTATED")

        second = scan_capabilities(FakeBlender())

        self.assertNotIn(
            "MUTATED",
            second["node_types"]["GeometryNodeJoinGeometry"]["semantic"]["typical_inputs"],
        )

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

        result = self._scan_with_fake_bpy(fake_bpy)

        node = result["node_types"]["GeometryNodeJoinGeometry"]
        self.assertTrue(node["metadata_complete"])
        self.assertEqual(node["inputs"][0]["name"], "Geometry")
        self.assertEqual(node["outputs"][0]["socket_type"], "NodeSocketGeometry")

    def test_scan_bpy_capabilities_stops_template_scan_at_none_and_caps_at_64(self):
        class FakeSocketTemplate:
            def __init__(self, index):
                self.name = f"Input {index}"
                self.identifier = f"Input_{index}"
                self.bl_socket_idname = "NodeSocketFloat"

        class GeometryNodeJoinGeometry:
            @classmethod
            def input_template(cls, index):
                if index < 70:
                    return FakeSocketTemplate(index)
                return None

            @classmethod
            def output_template(cls, index):
                if index == 0:
                    return FakeSocketTemplate(index)
                return None

        class FunctionNodeRandomValue:
            @classmethod
            def input_template(cls, index):
                return None

            @classmethod
            def output_template(cls, index):
                return None

        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return [GeometryNodeJoinGeometry]

        class FunctionNode:
            @classmethod
            def __subclasses__(cls):
                return [FunctionNodeRandomValue]

        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(4, 3, 0)),
            types=types.SimpleNamespace(GeometryNode=GeometryNode, FunctionNode=FunctionNode),
        )

        result = self._scan_with_fake_bpy(fake_bpy)

        self.assertEqual(len(result["node_types"]["GeometryNodeJoinGeometry"]["inputs"]), 64)
        self.assertEqual(
            result["node_types"]["GeometryNodeJoinGeometry"]["outputs"][0]["name"],
            "Input 0",
        )
        self.assertEqual(result["node_types"]["FunctionNodeRandomValue"]["inputs"], [])


if __name__ == "__main__":
    unittest.main()
