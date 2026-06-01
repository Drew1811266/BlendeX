import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blender_addon.blendex.executor import GeometryNodesExecutor


class FakeNodeTree:
    def __init__(self):
        self.nodes = {}
        self.links = []


class FakeModifier:
    def __init__(self, name):
        self.name = name
        self.type = "NODES"
        self.node_group = FakeNodeTree()
        self.props = {}
        self["blendex_owned"] = True

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]


class FakeObject:
    def __init__(self, name):
        self.name = name
        self.modifiers = {"BlendeX Geometry": FakeModifier("BlendeX Geometry")}


class FakeContext:
    def __init__(self):
        self.objects = {"Cube": FakeObject("Cube")}
        self.node_types = {"GeometryNodeJoinGeometry"}


class ExecutorTests(unittest.TestCase):
    def test_create_node_adds_node_to_tree(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_1",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry", "label": "Join Geometry"},
        )

        result = executor.execute(request)

        self.assertEqual(result["node_type"], "GeometryNodeJoinGeometry")
        self.assertEqual(result["label"], "Join Geometry")

    def test_create_node_rejects_unavailable_type(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_2",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeUnknown"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "NODE_TYPE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
