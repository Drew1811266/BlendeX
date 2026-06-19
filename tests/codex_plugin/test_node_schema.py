import types
import unittest

from codex_plugin.blendex_mcp.node_schema import normalize_node_capability, normalize_socket


class NodeSchemaTests(unittest.TestCase):
    def test_normalize_socket_accepts_legacy_string_sockets(self):
        socket = normalize_socket("Geometry", direction="input")

        self.assertEqual(
            socket,
            {
                "name": "Geometry",
                "identifier": "Geometry",
                "socket_type": "",
                "direction": "input",
                "is_multi_input": False,
                "is_field": False,
                "default_value": None,
                "enum_items": [],
            },
        )

    def test_normalize_socket_reads_richer_object_metadata(self):
        enum_items = [
            types.SimpleNamespace(identifier="FLOAT", name="Float"),
            types.SimpleNamespace(identifier="INT", name="Integer"),
        ]
        raw_socket = types.SimpleNamespace(
            name="Value",
            identifier="Value_001",
            bl_socket_idname="NodeSocketFloat",
            is_multi_input=True,
            is_field=True,
            default_value=(1.0, 2.0, 3.0),
            enum_items=enum_items,
        )

        socket = normalize_socket(raw_socket, direction="output")

        self.assertEqual(socket["name"], "Value")
        self.assertEqual(socket["identifier"], "Value_001")
        self.assertEqual(socket["socket_type"], "NodeSocketFloat")
        self.assertEqual(socket["direction"], "output")
        self.assertTrue(socket["is_multi_input"])
        self.assertTrue(socket["is_field"])
        self.assertEqual(socket["default_value"], [1.0, 2.0, 3.0])
        self.assertEqual(
            socket["enum_items"],
            [
                {"identifier": "FLOAT", "name": "Float"},
                {"identifier": "INT", "name": "Integer"},
            ],
        )

    def test_normalize_node_capability_converts_legacy_runtime_capabilities(self):
        capability = normalize_node_capability(
            "GeometryNodeJoinGeometry",
            {
                "display_name": "Join Geometry",
                "inputs": ["Geometry"],
                "outputs": ["Geometry"],
            },
        )

        self.assertEqual(capability["schema_version"], "node_capability.v2")
        self.assertEqual(capability["display_name"], "Join Geometry")
        self.assertTrue(capability["metadata_complete"])
        self.assertEqual(capability["inputs"][0]["identifier"], "Geometry")
        self.assertEqual(capability["outputs"][0]["direction"], "output")


if __name__ == "__main__":
    unittest.main()
