import sys
import types
import unittest

from blender_addon.blendex.capabilities import scan_bpy_capabilities, scan_capabilities


class CapabilityV2Tests(unittest.TestCase):
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

    def test_scan_capabilities_normalizes_legacy_runtime_sockets(self):
        runtime = types.SimpleNamespace(
            version=(5, 1, 2),
            node_types={
                "GeometryNodeJoinGeometry": {
                    "inputs": ["Geometry"],
                    "outputs": ["Geometry"],
                }
            },
        )

        result = scan_capabilities(runtime)

        node = result["node_types"]["GeometryNodeJoinGeometry"]
        self.assertEqual(node["schema_version"], "node_capability.v2")
        self.assertEqual(node["inputs"][0]["direction"], "input")
        self.assertEqual(node["outputs"][0]["direction"], "output")
        self.assertEqual(node["inputs"][0]["default_value"], None)
        self.assertEqual(node["inputs"][0]["enum_items"], [])

    def test_scan_bpy_capabilities_reads_richer_socket_template_metadata(self):
        class FakeEnumItem:
            def __init__(self, identifier, name):
                self.identifier = identifier
                self.name = name

        class FakeSocketTemplate:
            name = "Scale"
            identifier = "Scale"
            bl_socket_idname = "NodeSocketVector"
            is_multi_input = True
            is_field = True
            default_value = (1.0, 1.0, 1.0)
            enum_items = [FakeEnumItem("VECTOR", "Vector")]

        class GeometryNodeTransform:
            @classmethod
            def input_template(cls, index):
                if index == 0:
                    return FakeSocketTemplate()
                return None

            @classmethod
            def output_template(cls, index):
                return None

        class GeometryNode:
            @classmethod
            def __subclasses__(cls):
                return [GeometryNodeTransform]

        fake_bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(version=(5, 1, 2)),
            types=types.SimpleNamespace(GeometryNode=GeometryNode),
        )

        result = self._scan_with_fake_bpy(fake_bpy)

        socket = result["node_types"]["GeometryNodeTransform"]["inputs"][0]
        self.assertEqual(socket["socket_type"], "NodeSocketVector")
        self.assertEqual(socket["direction"], "input")
        self.assertTrue(socket["is_multi_input"])
        self.assertTrue(socket["is_field"])
        self.assertEqual(socket["default_value"], [1.0, 1.0, 1.0])
        self.assertEqual(socket["enum_items"], [{"identifier": "VECTOR", "name": "Vector"}])


if __name__ == "__main__":
    unittest.main()
