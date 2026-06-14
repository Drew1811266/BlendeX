import pathlib
import sys

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "blender_addon"))

import blendex
from blendex.batches import execute_batch, undo_last_batch
from blendex.executor import GeometryNodesExecutor
from blendex_protocol.messages import OperationRequest


class SmokeContext:
    def __init__(self, obj):
        self.objects = {obj.name: obj}
        self.node_types = {
            "GeometryNodeJoinGeometry": {
                "inputs": [{"name": "Geometry", "socket_type": "NodeSocketGeometry"}],
                "outputs": [{"name": "Geometry", "socket_type": "NodeSocketGeometry"}],
            }
        }


def main():
    blendex.register()
    try:
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object

        executor = GeometryNodesExecutor(SmokeContext(obj))
        modifier = executor.execute(
            OperationRequest(
                id="smoke_modifier",
                type="geometry_nodes.create_modifier",
                target={"object_id": obj.name},
                params={"modifier_id": "BlendeX Geometry"},
            )
        )
        assert modifier["blendex_owned"] is True

        node_a = executor.execute(
            OperationRequest(
                id="smoke_node_a",
                type="geometry_nodes.create_node",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={"node_type": "GeometryNodeJoinGeometry", "label": "Join A"},
            )
        )
        node_b = executor.execute(
            OperationRequest(
                id="smoke_node_b",
                type="geometry_nodes.create_node",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={"node_type": "GeometryNodeJoinGeometry", "label": "Join B"},
            )
        )
        assert node_a["node_type"] == "GeometryNodeJoinGeometry"
        assert node_b["node_type"] == "GeometryNodeJoinGeometry"

        tree = executor.execute(
            OperationRequest(
                id="smoke_tree",
                type="geometry_nodes.inspect_tree",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={},
            )
        )
        created_nodes = {
            node.get("label"): node
            for node in tree["nodes"]
            if node.get("label") in {"Join A", "Join B"}
        }
        assert set(created_nodes) == {"Join A", "Join B"}
        assert created_nodes["Join A"]["node_type"] == "GeometryNodeJoinGeometry"
        assert created_nodes["Join B"]["node_type"] == "GeometryNodeJoinGeometry"

        batch = execute_batch(
            {
                "target": {"object_id": obj.name},
                "params": {
                    "confirmed": True,
                    "confirmation_id": "smoke_confirmed_batch",
                    "summary": "Smoke batch",
                    "operations": [
                        {
                            "id": "smoke_batch_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                            "params": {
                                "node_type": "GeometryNodeJoinGeometry",
                                "label": "Smoke Batch Join",
                            },
                        }
                    ],
                },
            },
            executor,
        )
        assert batch["status"] == "succeeded"
        assert batch["operations"][0]["ok"] is True

        undo = undo_last_batch()
        assert undo["undo_status"] == "undone"
    finally:
        blendex.unregister()


if __name__ == "__main__":
    main()
