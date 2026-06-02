import unittest
from unittest.mock import patch

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


class FakeSocket:
    def __init__(self, name):
        self.name = name


class FakeBlenderNode:
    def __init__(self, name, bl_idname):
        self.name = name
        self.bl_idname = bl_idname
        self.label = ""
        self.location = [0, 0]


class FakeBlenderLink:
    def __init__(self, from_node, from_socket, to_node, to_socket):
        self.from_node = from_node
        self.from_socket = from_socket
        self.to_node = to_node
        self.to_socket = to_socket


class FakeBlenderNodeCollection:
    def __init__(self):
        self.created = []

    def new(self, type):
        node = FakeBlenderNode(f"{type}.{len(self.created) + 1:03d}", type)
        self.created.append(node)
        return node

    def __iter__(self):
        return iter(self.created)


class ExecutorTests(unittest.TestCase):
    def test_create_node_adds_node_to_tree(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_1",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry", "label": "Join Geometry", "location": (0, 0)},
        )

        result = executor.execute(request)

        self.assertEqual(result["node_type"], "GeometryNodeJoinGeometry")
        self.assertEqual(result["label"], "Join Geometry")
        self.assertEqual(result["location"], [0, 0])

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

    def test_inspect_tree_returns_nodes_and_structured_links(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes["node_1"] = {"id": "node_1", "node_type": "GeometryNodeInput", "label": "Input"}
        tree.nodes["node_2"] = {"id": "node_2", "node_type": "GeometryNodeOutput", "label": "Output"}
        tree.links.append(
            {
                "from_node": "node_1",
                "from_socket": "Geometry",
                "to_node": "node_2",
                "to_socket": "Geometry",
            }
        )
        from_node = FakeBlenderNode("Group Input", "NodeGroupInput")
        to_node = FakeBlenderNode("Group Output", "NodeGroupOutput")
        tree.links.append(
            FakeBlenderLink(
                from_node,
                FakeSocket("Geometry"),
                to_node,
                FakeSocket("Geometry"),
            )
        )
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_3",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        result = executor.execute(request)

        self.assertEqual(
            result["nodes"],
            [
                {"id": "node_1", "node_type": "GeometryNodeInput", "label": "Input"},
                {"id": "node_2", "node_type": "GeometryNodeOutput", "label": "Output"},
            ],
        )
        self.assertEqual(
            result["links"],
            [
                {
                    "from_node": "node_1",
                    "from_socket": "Geometry",
                    "to_node": "node_2",
                    "to_socket": "Geometry",
                },
                {
                    "from_node": "Group Input",
                    "from_socket": "Geometry",
                    "to_node": "Group Output",
                    "to_socket": "Geometry",
                },
            ],
        )

    def test_unsupported_operation_raises_unsupported_operation(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_4",
            type="geometry_nodes.delete_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "UNSUPPORTED_OPERATION")

    def test_missing_object_raises_object_not_found(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_5",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Missing", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "OBJECT_NOT_FOUND")

    def test_missing_modifier_raises_modifier_not_found(self):
        executor = GeometryNodesExecutor(FakeContext())
        request = OperationRequest(
            id="req_6",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Cube", "modifier_id": "Missing"},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "MODIFIER_NOT_FOUND")

    def test_non_nodes_modifier_raises_modifier_not_found(self):
        context = FakeContext()
        modifier = context.objects["Cube"].modifiers["BlendeX Geometry"]
        modifier.type = "SUBSURF"
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_7",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "MODIFIER_NOT_FOUND")

    def test_create_node_uses_blender_like_node_collection(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_8",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "node_type": "GeometryNodeJoinGeometry",
                "label": "Join Geometry",
                "location": (12, 34),
            },
        )

        result = executor.execute(request)

        self.assertEqual(result["id"], "GeometryNodeJoinGeometry.001")
        self.assertEqual(result["node_type"], "GeometryNodeJoinGeometry")
        self.assertEqual(result["label"], "Join Geometry")
        self.assertEqual(result["location"], [12, 34])
        self.assertEqual(tree.nodes.created[0].location, (12, 34))

    def test_node_tree_failure_raises_node_tree_not_found(self):
        modifier = FakeModifier("Detached Geometry")
        modifier.node_group = None
        executor = GeometryNodesExecutor(FakeContext())

        with patch.dict("sys.modules", {"bpy": None}):
            with self.assertRaises(BlendexError) as raised:
                executor._node_tree(modifier)

        self.assertEqual(raised.exception.code, "NODE_TREE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
