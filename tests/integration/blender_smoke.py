import pathlib
import sys

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "blender_addon"))

import blendex
from blendex.executor import GeometryNodesExecutor
from blendex_protocol.messages import OperationRequest


class SmokeContext:
    def __init__(self, obj):
        self.objects = {obj.name: obj}
        self.node_types = {"GeometryNodeJoinGeometry"}


def main():
    blendex.register()
    try:
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object
        modifier = obj.modifiers.new("BlendeX Geometry", "NODES")
        modifier["blendex_owned"] = True

        request = OperationRequest(
            id="smoke_1",
            type="geometry_nodes.create_node",
            target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
            params={"node_type": "GeometryNodeJoinGeometry", "label": "Join Geometry"},
        )
        result = GeometryNodesExecutor(SmokeContext(obj)).execute(request)
        assert result["node_type"] == "GeometryNodeJoinGeometry"
    finally:
        blendex.unregister()


if __name__ == "__main__":
    main()
