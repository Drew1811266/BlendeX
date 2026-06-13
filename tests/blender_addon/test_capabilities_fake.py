import sys
import types
import unittest

from blender_addon.blendex.capabilities import scan_bpy_capabilities, scan_capabilities
from codex_plugin.blendex_mcp.catalog import semantic_for_node


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
                "geometry_nodes.create_modifier",
                "geometry_nodes.create_node",
                "geometry_nodes.inspect_tree",
                "geometry_nodes.label_node",
                "geometry_nodes.link_sockets",
                "geometry_nodes.mark_ownership",
                "geometry_nodes.set_socket_value",
                "safety.batch_history",
                "safety.dry_run",
                "safety.execute_batch",
                "safety.inspect_batch",
                "safety.undo_last_batch",
                "safety.validate_batch",
                "scene.create_carrier_mesh",
                "scene.inspect",
            ],
        )

    def test_scan_advertises_batch_safety_operations(self):
        result = scan_capabilities(FakeBlender())

        self.assertIn("geometry_nodes.create_modifier", result["supported_operations"])
        self.assertIn("geometry_nodes.link_sockets", result["supported_operations"])
        self.assertIn("geometry_nodes.set_socket_value", result["supported_operations"])
        self.assertIn("geometry_nodes.label_node", result["supported_operations"])
        self.assertIn("geometry_nodes.mark_ownership", result["supported_operations"])
        self.assertIn("safety.validate_batch", result["supported_operations"])
        self.assertIn("safety.dry_run", result["supported_operations"])
        self.assertIn("safety.execute_batch", result["supported_operations"])
        self.assertIn("safety.batch_history", result["supported_operations"])
        self.assertIn("safety.inspect_batch", result["supported_operations"])
        self.assertIn("safety.undo_last_batch", result["supported_operations"])

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

    def test_scan_bpy_capabilities_discovers_dir_candidates_validated_by_geometry_tree(self):
        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return []

        class FunctionNode:
            @classmethod
            def __subclasses__(cls):
                return []

        class ShaderNode:
            @classmethod
            def __subclasses__(cls):
                return []

        valid_node_identifiers = {
            "GeometryNodeJoinGeometry",
            "FunctionNodeRandomValue",
            "ShaderNodeMath",
            "ShaderNodeVectorMath",
            "NodeGroupInput",
            "NodeGroupOutput",
        }

        class FakeNodes:
            def __init__(self):
                self.created = []
                self.removed = []

            def new(self, type):
                if type not in valid_node_identifiers:
                    raise RuntimeError(f"{type} is not valid in a GeometryNodeTree")
                node = types.SimpleNamespace(identifier=type)
                self.created.append(node)
                return node

            def remove(self, node):
                self.removed.append(node)

        class FakeNodeGroup:
            def __init__(self, name, tree_type):
                self.name = name
                self.tree_type = tree_type
                self.nodes = FakeNodes()

        class FakeNodeGroups:
            def __init__(self):
                self.created = []
                self.removed = []

            def new(self, name, tree_type):
                group = FakeNodeGroup(name, tree_type)
                self.created.append(group)
                return group

            def remove(self, group):
                self.removed.append(group)

        fake_node_groups = FakeNodeGroups()
        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(5, 1, 2)),
            types=types.SimpleNamespace(
                GeometryNode=GeometryNode,
                FunctionNode=FunctionNode,
                ShaderNode=ShaderNode,
                GeometryNodeJoinGeometry=type("GeometryNodeJoinGeometry", (), {}),
                FunctionNodeRandomValue=type("FunctionNodeRandomValue", (), {}),
                ShaderNodeMath=type("ShaderNodeMath", (), {}),
                ShaderNodeVectorMath=type("ShaderNodeVectorMath", (), {}),
                ShaderNodeBsdfPrincipled=type("ShaderNodeBsdfPrincipled", (), {}),
                NodeGroupInput=type("NodeGroupInput", (), {}),
                NodeGroupOutput=type("NodeGroupOutput", (), {}),
            ),
            data=types.SimpleNamespace(node_groups=fake_node_groups),
        )

        result = self._scan_with_fake_bpy(fake_bpy)

        self.assertEqual(result["blender_version"], [5, 1, 2])
        self.assertEqual(
            set(result["node_types"]),
            valid_node_identifiers,
        )
        self.assertNotIn("ShaderNodeBsdfPrincipled", result["node_types"])
        self.assertEqual(len(fake_node_groups.created), 1)
        self.assertEqual(fake_node_groups.created[0].tree_type, "GeometryNodeTree")
        self.assertEqual(fake_node_groups.removed, fake_node_groups.created)
        self.assertEqual(
            len(fake_node_groups.created[0].nodes.removed),
            len(valid_node_identifiers),
        )

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

    def test_semantic_for_node_returns_independent_metadata(self):
        first = semantic_for_node("GeometryNodeJoinGeometry")
        first["typical_inputs"].append("MUTATED")

        second = semantic_for_node("GeometryNodeJoinGeometry")

        self.assertNotIn("MUTATED", second["typical_inputs"])

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
