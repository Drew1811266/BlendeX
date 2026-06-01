from typing import Any, Dict

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


class GeometryNodesExecutor:
    def __init__(self, context: Any):
        self.context = context

    def execute(self, request: OperationRequest) -> Dict[str, Any]:
        validate_request(request)
        if request.type == "geometry_nodes.create_node":
            return self._create_node(request)
        if request.type == "geometry_nodes.inspect_tree":
            return self._inspect_tree(request)
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Executor does not implement operation: {request.type}",
            retry_hint="Call capabilities.supported_operations before planning.",
        )

    def _object(self, object_id: str) -> Any:
        obj = self.context.objects.get(object_id)
        if obj is None:
            raise BlendexError("OBJECT_NOT_FOUND", f"Object not found: {object_id}")
        return obj

    def _modifier(self, obj: Any, modifier_id: str) -> Any:
        modifier = obj.modifiers.get(modifier_id)
        if modifier is None:
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier not found: {modifier_id}")
        if getattr(modifier, "type", "") != "NODES":
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier is not a Geometry Nodes modifier: {modifier_id}")
        return modifier

    def _create_node(self, request: OperationRequest) -> Dict[str, Any]:
        node_type = request.params["node_type"]
        if node_type not in self.context.node_types:
            raise BlendexError(
                "NODE_TYPE_NOT_FOUND",
                f"Node type is unavailable: {node_type}",
                retry_hint="Refresh capabilities and choose a node type reported by Blender.",
            )
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        tree = self._node_tree(modifier)
        label = request.params.get("label", node_type)
        location = request.params.get("location", [0, 0])
        if hasattr(tree.nodes, "new"):
            node = tree.nodes.new(type=node_type)
            node.label = label
            node.location = location
            return {"id": node.name, "node_type": node_type, "label": label, "location": list(location)}
        node_id = f"node_{len(tree.nodes) + 1}"
        node_data = {"id": node_id, "node_type": node_type, "label": label, "location": location}
        tree.nodes[node_id] = node_data
        return node_data

    def _inspect_tree(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        tree = self._node_tree(modifier)
        if hasattr(tree.nodes, "values"):
            nodes = list(tree.nodes.values())
        else:
            nodes = [{"id": node.name, "node_type": node.bl_idname, "label": node.label} for node in tree.nodes]
        return {"nodes": nodes, "links": [str(link) for link in tree.links]}

    def _node_tree(self, modifier: Any) -> Any:
        tree = getattr(modifier, "node_group", None)
        if tree is not None:
            return tree
        try:
            import bpy

            tree = bpy.data.node_groups.new(f"{modifier.name} Node Tree", "GeometryNodeTree")
            modifier.node_group = tree
            return tree
        except Exception as exc:
            raise BlendexError(
                "NODE_TREE_NOT_FOUND",
                f"Could not create or access Geometry Nodes tree for modifier: {modifier.name}",
                details={"exception": str(exc)},
            )
