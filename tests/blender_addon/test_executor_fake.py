import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blender_addon.blendex.executor import GeometryNodesExecutor


class FakeNodeTree:
    def __init__(self, name="BlendeX Geometry Node Tree"):
        self.name = name
        self.nodes = {}
        self.links = []
        self.props = {}

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)


class ClearingNodeGroupModifier:
    def __init__(self, name, owned=True):
        self.name = name
        self.type = "NODES"
        self._node_group = None
        self.props = {}
        if owned:
            self["blendex_owned"] = True

    @property
    def node_group(self):
        return self._node_group

    @node_group.setter
    def node_group(self, value):
        self._node_group = value
        self.props.clear()

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)


class FakeModifier:
    def __init__(self, name, owned=True):
        self.name = name
        self.type = "NODES"
        self.node_group = FakeNodeTree(f"{name} Node Tree")
        self.props = {}
        if owned:
            self["blendex_owned"] = True
            self.node_group["blendex_owned"] = True

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)


class FakeNonNodesModifier:
    def __init__(self, name):
        self.name = name
        self.type = "BEVEL"


class FakeModifierCollection(dict):
    def new(self, name, type):
        modifier = FakeModifier(name, owned=False)
        modifier.type = type
        self[name] = modifier
        return modifier


class FakeObject:
    def __init__(self, name):
        self.name = name
        self.modifiers = FakeModifierCollection({"BlendeX Geometry": FakeModifier("BlendeX Geometry")})


class FakeContext:
    def __init__(self):
        self.objects = {"Cube": FakeObject("Cube")}
        self.node_types = {"GeometryNodeJoinGeometry"}


class FakeSocket:
    def __init__(self, name, socket_type="NodeSocketGeometry", default_value=None, identifier=None):
        self.name = name
        self.identifier = identifier or name
        self.bl_socket_idname = socket_type
        self.type = socket_type
        self.default_value = default_value
        self.owner = None


class FakeSocketList:
    def __init__(self, sockets):
        self.sockets = list(sockets)

    def get(self, name):
        for socket in self.sockets:
            if socket.name == name or socket.identifier == name:
                return socket
        return None

    def __iter__(self):
        return iter(self.sockets)

    def __len__(self):
        return len(self.sockets)


class FakeVectorDefault:
    def __iter__(self):
        return iter((1.0, 2.0, 3.0))


class FakeBlenderNode:
    def __init__(self, name, bl_idname):
        self.name = name
        self.bl_idname = bl_idname
        self.label = ""
        self.location = [0, 0]
        self.inputs = FakeSocketList([FakeSocket("Geometry")])
        self.outputs = FakeSocketList([FakeSocket("Geometry")])
        for socket in self.inputs:
            socket.owner = self
        for socket in self.outputs:
            socket.owner = self


class FakeBlenderLink:
    def __init__(self, from_node, from_socket, to_node, to_socket):
        self.from_node = from_node
        self.from_socket = from_socket
        self.to_node = to_node
        self.to_socket = to_socket


class FakeLinkCollection:
    def __init__(self):
        self.created = []

    def new(self, from_socket, to_socket):
        link = FakeBlenderLink(from_socket.owner, from_socket, to_socket.owner, to_socket)
        self.created.append(link)
        return link

    def append(self, link):
        self.created.append(link)

    def __iter__(self):
        return iter(self.created)

    def __len__(self):
        return len(self.created)


class FakeBlenderNodeCollection:
    def __init__(self):
        self.created = []

    def new(self, type):
        node = FakeBlenderNode(f"{type}.{len(self.created) + 1:03d}", type)
        if type == "ShaderNodeValue":
            node.inputs = FakeSocketList([FakeSocket("Value", "NodeSocketFloat", 0.0)])
            node.outputs = FakeSocketList([FakeSocket("Value", "NodeSocketFloat", 0.0)])
            for socket in node.inputs:
                socket.owner = node
            for socket in node.outputs:
                socket.owner = node
        self.created.append(node)
        return node

    def get(self, name):
        for node in self.created:
            if node.name == name:
                return node
        return None

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

    def test_create_node_requires_blendex_owned_modifier(self):
        context = FakeContext()
        context.objects["Cube"].modifiers["User Geometry"] = FakeModifier("User Geometry", owned=False)
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_owned",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "User Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "OWNERSHIP_REQUIRED")

    def test_create_node_requires_blendex_owned_node_group(self):
        context = FakeContext()
        modifier = context.objects["Cube"].modifiers["BlendeX Geometry"]
        modifier.node_group.props.clear()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_owned_tree",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "OWNERSHIP_REQUIRED")

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

        self.assertEqual(result["object_id"], "Cube")
        self.assertEqual(result["modifier_id"], "BlendeX Geometry")
        self.assertEqual(result["node_group_id"], "BlendeX Geometry Node Tree")
        self.assertTrue(result["blendex_owned"])
        self.assertEqual(result["nodes"][0]["id"], "node_1")
        self.assertEqual(result["nodes"][1]["node_type"], "GeometryNodeOutput")
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
                    "socket_type": "NodeSocketGeometry",
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
        self.assertEqual(
            result["inputs"],
            [{"name": "Geometry", "identifier": "Geometry", "socket_type": "NodeSocketGeometry", "has_default": True, "default_value": None}],
        )
        self.assertEqual(result["outputs"][0]["socket_type"], "NodeSocketGeometry")
        self.assertEqual(tree.nodes.created[0].location, (12, 34))

    def test_create_node_rejects_invalid_location_before_mutation(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_bad_location",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "node_type": "GeometryNodeJoinGeometry",
                "location": "not-a-location",
            },
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(tree.nodes.created, [])

    def test_create_node_rejects_invalid_label_before_mutation(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_bad_label",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "node_type": "GeometryNodeJoinGeometry",
                "label": 123,
            },
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(tree.nodes.created, [])

    def test_validate_create_node_checks_type_and_ownership_without_mutation(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_validate_node",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry"},
        )

        result = executor.validate(request)

        self.assertEqual(result, {"validated": True})
        self.assertEqual(tree.nodes.created, [])

    def test_validate_create_node_rejects_unavailable_type_without_mutation(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_validate_node",
            type="geometry_nodes.create_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_type": "ShaderNodeValue"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.validate(request)

        self.assertEqual(raised.exception.code, "NODE_TYPE_NOT_FOUND")
        self.assertEqual(tree.nodes.created, [])

    def test_create_modifier_creates_or_reuses_nodes_modifier_and_marks_owned(self):
        context = FakeContext()
        del context.objects["Cube"].modifiers["BlendeX Geometry"]
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": "BlendeX Geometry"},
        )

        result = executor.execute(request)
        reused = executor.execute(request)

        modifier = context.objects["Cube"].modifiers["BlendeX Geometry"]
        self.assertIs(modifier, context.objects["Cube"].modifiers["BlendeX Geometry"])
        self.assertEqual(result["modifier_id"], "BlendeX Geometry")
        self.assertEqual(result["modifier_type"], "NODES")
        self.assertEqual(reused["modifier_id"], "BlendeX Geometry")
        self.assertTrue(result["blendex_owned"])
        self.assertTrue(modifier.get("blendex_owned"))
        self.assertTrue(modifier.node_group.get("blendex_owned"))

    def test_validate_create_modifier_rejects_existing_non_nodes_modifier(self):
        context = FakeContext()
        context.objects["Cube"].modifiers["BlendeX Geometry"] = FakeNonNodesModifier("BlendeX Geometry")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_validate_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": "BlendeX Geometry"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.validate(request)

        self.assertEqual(raised.exception.code, "MODIFIER_NOT_FOUND")

    def test_create_modifier_rejects_empty_modifier_id_before_mutation(self):
        context = FakeContext()
        del context.objects["Cube"].modifiers["BlendeX Geometry"]
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_bad_modifier",
            type="geometry_nodes.create_modifier",
            target={"object_id": "Cube"},
            params={"modifier_id": ""},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(context.objects["Cube"].modifiers, {})

    def test_node_tree_creation_restores_modifier_ownership_after_assignment(self):
        context = FakeContext()
        modifier = ClearingNodeGroupModifier("BlendeX Geometry", owned=True)
        context.objects["Cube"].modifiers["BlendeX Geometry"] = modifier
        executor = GeometryNodesExecutor(context)

        class FakeNodeGroups:
            def new(self, name, tree_type):
                return FakeNodeTree(name)

        fake_bpy = type(
            "FakeBpy",
            (),
            {"data": type("FakeData", (), {"node_groups": FakeNodeGroups()})()},
        )()

        with patch.dict("sys.modules", {"bpy": fake_bpy}):
            tree = executor._node_tree(modifier)

        self.assertIs(modifier.node_group, tree)
        self.assertTrue(modifier.get("blendex_owned"))
        self.assertTrue(tree.get("blendex_owned"))

    def test_mark_ownership_marks_existing_modifier_and_node_group_owned(self):
        context = FakeContext()
        modifier = context.objects["Cube"].modifiers["BlendeX Geometry"]
        modifier.props.clear()
        modifier.node_group.props.clear()
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_mark",
            type="geometry_nodes.mark_ownership",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        result = executor.execute(request)

        self.assertTrue(result["blendex_owned"])
        self.assertTrue(modifier.get("blendex_owned"))
        self.assertTrue(modifier.node_group.get("blendex_owned"))

    def test_set_socket_value_updates_input_default(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        node = tree.nodes.new(type="ShaderNodeValue")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_value",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_id": node.name, "socket": "Value", "value": 4.25},
        )

        result = executor.execute(request)

        self.assertEqual(result["node_id"], node.name)
        self.assertEqual(result["socket"], "Value")
        self.assertEqual(result["value"], 4.25)
        self.assertEqual(node.inputs.get("Value").default_value, 4.25)

    def test_set_socket_value_rejects_incompatible_value_type(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        node = tree.nodes.new(type="ShaderNodeValue")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_value_bad",
            type="geometry_nodes.set_socket_value",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_id": node.name, "socket": "Value", "value": "not a float"},
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "VALUE_TYPE_MISMATCH")

    def test_link_sockets_creates_link_between_compatible_sockets(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = FakeLinkCollection()
        from_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_link",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": from_node.name,
                "from_socket": "Geometry",
                "to_node": to_node.name,
                "to_socket": "Geometry",
            },
        )

        result = executor.execute(request)

        self.assertEqual(result["from_node"], from_node.name)
        self.assertEqual(result["to_node"], to_node.name)
        self.assertEqual(result["socket_type"], "NodeSocketGeometry")
        self.assertEqual(len(tree.links), 1)

    def test_link_sockets_rejects_mismatched_socket_types(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        from_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="ShaderNodeValue")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_link_bad",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": from_node.name,
                "from_socket": "Geometry",
                "to_node": to_node.name,
                "to_socket": "Value",
            },
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "SOCKET_TYPE_MISMATCH")

    def test_link_sockets_validates_source_socket_before_destination_node(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        from_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_link_order",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": from_node.name,
                "from_socket": "Missing",
                "to_node": "Missing Destination",
                "to_socket": "Geometry",
            },
        )

        with self.assertRaises(BlendexError) as raised:
            executor.validate(request)

        self.assertEqual(raised.exception.code, "SOCKET_NOT_FOUND")

    def test_link_sockets_rejects_existing_input_link_without_replacing(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = FakeLinkCollection()
        first_source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        second_source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        existing = tree.links.new(first_source.outputs.get("Geometry"), to_node.inputs.get("Geometry"))
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_link_existing",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": second_source.name,
                "from_socket": "Geometry",
                "to_node": to_node.name,
                "to_socket": "Geometry",
            },
        )

        with self.assertRaises(BlendexError) as raised:
            executor.execute(request)

        self.assertEqual(raised.exception.code, "LINK_NOT_ALLOWED")
        self.assertEqual(len(tree.links), 1)
        self.assertIs(tree.links.created[0], existing)

    def test_link_sockets_allows_existing_link_on_multi_input_socket(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = FakeLinkCollection()
        first_source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        second_source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node.inputs.get("Geometry").is_multi_input = True
        executor = GeometryNodesExecutor(context)

        executor.execute(
            OperationRequest(
                id="req_link_multi_first",
                type="geometry_nodes.link_sockets",
                target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                params={
                    "from_node": first_source.name,
                    "from_socket": "Geometry",
                    "to_node": to_node.name,
                    "to_socket": "Geometry",
                },
            )
        )
        result = executor.execute(
            OperationRequest(
                id="req_link_multi_second",
                type="geometry_nodes.link_sockets",
                target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
                params={
                    "from_node": second_source.name,
                    "from_socket": "Geometry",
                    "to_node": to_node.name,
                    "to_socket": "Geometry",
                },
            )
        )

        self.assertEqual(result["to_node"], to_node.name)
        self.assertEqual(len(tree.links), 2)

    def test_label_node_updates_label(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_label",
            type="geometry_nodes.label_node",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={"node_id": node.name, "label": "Readable Join"},
        )

        result = executor.execute(request)

        self.assertEqual(result["node_id"], node.name)
        self.assertEqual(result["label"], "Readable Join")
        self.assertEqual(node.label, "Readable Join")

    def test_inspect_tree_returns_blender_like_socket_summaries_and_ownership(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = FakeLinkCollection()
        from_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        tree.links.new(from_node.outputs.get("Geometry"), to_node.inputs.get("Geometry"))
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_inspect_sockets",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        result = executor.execute(request)

        self.assertEqual(result["object_id"], "Cube")
        self.assertEqual(result["modifier_id"], "BlendeX Geometry")
        self.assertEqual(result["node_group_id"], "BlendeX Geometry Node Tree")
        self.assertTrue(result["blendex_owned"])
        self.assertEqual(result["nodes"][0]["inputs"][0]["name"], "Geometry")
        self.assertEqual(result["nodes"][0]["outputs"][0]["socket_type"], "NodeSocketGeometry")
        self.assertEqual(result["links"][0]["from_node"], from_node.name)
        self.assertEqual(result["links"][0]["socket_type"], "NodeSocketGeometry")

    def test_inspect_tree_converts_socket_default_values_to_json_safe_values(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        node.inputs = FakeSocketList(
            [FakeSocket("Vector", "NodeSocketVector", FakeVectorDefault())]
        )
        for socket in node.inputs:
            socket.owner = node
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_inspect_defaults",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        result = executor.execute(request)

        self.assertEqual(result["nodes"][0]["inputs"][0]["default_value"], [1.0, 2.0, 3.0])

    def test_link_sockets_fallback_records_node_endpoints(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = []
        from_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_link_fallback",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": from_node.name,
                "from_socket": "Geometry",
                "to_node": to_node.name,
                "to_socket": "Geometry",
            },
        )

        result = executor.execute(request)

        self.assertEqual(result["from_node"], from_node.name)
        self.assertEqual(result["to_node"], to_node.name)
        self.assertEqual(tree.links[0]["from_node"], from_node.name)
        self.assertEqual(tree.links[0]["to_node"], to_node.name)

    def test_link_sockets_fallback_rejects_existing_input_link(self):
        context = FakeContext()
        tree = context.objects["Cube"].modifiers["BlendeX Geometry"].node_group
        tree.nodes = FakeBlenderNodeCollection()
        tree.links = []
        first_source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        second_source = tree.nodes.new(type="GeometryNodeJoinGeometry")
        to_node = tree.nodes.new(type="GeometryNodeJoinGeometry")
        executor = GeometryNodesExecutor(context)
        first_request = OperationRequest(
            id="req_link_fallback_first",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": first_source.name,
                "from_socket": "Geometry",
                "to_node": to_node.name,
                "to_socket": "Geometry",
            },
        )
        second_request = OperationRequest(
            id="req_link_fallback_second",
            type="geometry_nodes.link_sockets",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={
                "from_node": second_source.name,
                "from_socket": "Geometry",
                "to_node": to_node.name,
                "to_socket": "Geometry",
            },
        )

        executor.execute(first_request)
        with self.assertRaises(BlendexError) as raised:
            executor.execute(second_request)

        self.assertEqual(raised.exception.code, "LINK_NOT_ALLOWED")
        self.assertEqual(len(tree.links), 1)
        self.assertEqual(tree.links[0]["from_node"], first_source.name)

    def test_node_tree_failure_raises_node_tree_not_found(self):
        modifier = FakeModifier("Detached Geometry")
        modifier.node_group = None
        executor = GeometryNodesExecutor(FakeContext())

        with patch.dict("sys.modules", {"bpy": None}):
            with self.assertRaises(BlendexError) as raised:
                executor._node_tree(modifier)

        self.assertEqual(raised.exception.code, "NODE_TREE_NOT_FOUND")

    def test_inspect_tree_does_not_create_missing_node_group(self):
        context = FakeContext()
        modifier = context.objects["Cube"].modifiers["BlendeX Geometry"]
        modifier.node_group = None
        executor = GeometryNodesExecutor(context)
        request = OperationRequest(
            id="req_inspect_missing_tree",
            type="geometry_nodes.inspect_tree",
            target={"object_id": "Cube", "modifier_id": "BlendeX Geometry"},
            params={},
        )

        class FakeNodeGroups:
            def __init__(self):
                self.created = []

            def new(self, name, tree_type):
                tree = FakeNodeTree(name)
                self.created.append((name, tree_type, tree))
                return tree

        fake_node_groups = FakeNodeGroups()
        fake_bpy = type(
            "FakeBpy",
            (),
            {"data": type("FakeData", (), {"node_groups": fake_node_groups})()},
        )()

        with patch.dict("sys.modules", {"bpy": fake_bpy}):
            with self.assertRaises(BlendexError) as raised:
                executor.execute(request)

        self.assertEqual(raised.exception.code, "NODE_TREE_NOT_FOUND")
        self.assertIsNone(modifier.node_group)
        self.assertEqual(fake_node_groups.created, [])


if __name__ == "__main__":
    unittest.main()
