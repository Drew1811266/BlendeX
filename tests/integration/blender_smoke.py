import os
import pathlib
import sys
import traceback

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "blender_addon"))

import blendex
from blendex.scene import bpy_scene_context
from blendex.batches import execute_batch, undo_last_batch
from blendex.executor import GeometryNodesExecutor
from codex_plugin.blendex_mcp.benchmark import load_heldout_prompts
from codex_plugin.blendex_mcp.graph_planner import plan_graph
from codex_plugin.blendex_mcp.recipes import REGISTRY
from blendex_protocol.messages import OperationRequest


class SmokeContext:
    def __init__(self):
        self._context = bpy_scene_context()
        self.node_types = {
            "FunctionNodeRandomValue": {},
            "GeometryNodeCaptureAttribute": {},
            "GeometryNodeDistributePointsOnFaces": {},
            "GeometryNodeInstanceOnPoints": {},
            "GeometryNodeJoinGeometry": {},
            "GeometryNodeMeshCube": {},
            "GeometryNodeMeshLine": {},
            "GeometryNodeRealizeInstances": {},
            "GeometryNodeSetPosition": {},
            "GeometryNodeStoreNamedAttribute": {},
            "GeometryNodeTransform": {},
            "NodeGroupInput": {},
            "NodeGroupOutput": {},
        }

    def __getattr__(self, name):
        return getattr(self._context, name)


def _carrier_name(operations):
    for operation in operations:
        if operation.get("type") == "scene.create_carrier_mesh":
            return operation.get("params", {}).get("name", "BlendeX Carrier")
    raise AssertionError("Recipe did not create a carrier mesh")


def _execute_recipe(executor, recipe_id, params, expected_label_fragments, minimum_links):
    operations = REGISTRY.build(recipe_id, params)
    object_id = _carrier_name(operations)
    batch = execute_batch(
        {
            "target": {"object_id": object_id},
            "params": {
                "confirmed": True,
                "confirmation_id": f"smoke_{recipe_id}",
                "summary": f"Smoke {recipe_id}",
                "operations": operations,
            },
        },
        executor,
    )
    assert batch["status"] == "succeeded", batch
    assert batch["execution_summary"]["failed_operations"] == 0

    tree = executor.execute(
        OperationRequest(
            id=f"inspect_{recipe_id}",
            type="geometry_nodes.inspect_tree",
            target={"object_id": object_id, "modifier_id": "BlendeX Geometry"},
            params={},
        )
    )
    labels = {node.get("label", "") for node in tree["nodes"]}
    for fragment in expected_label_fragments:
        assert any(fragment in label for label in labels), (fragment, labels)
    assert len(tree["links"]) >= minimum_links, tree["links"]

    undo = undo_last_batch()
    assert undo["undo_status"] == "undone", undo


def _execute_generated_graph(executor, item):
    plan = plan_graph(item["prompt"])
    assert plan["mode"] == "graph_plan", plan
    assert plan["validation"]["valid"], plan["validation"]
    operations = plan["operations"]
    object_id = _carrier_name(operations)
    batch = execute_batch(
        {
            "target": {"object_id": object_id},
            "params": {
                "confirmed": True,
                "confirmation_id": f"generated_{item['id']}",
                "summary": f"Generated graph smoke {item['id']}",
                "operations": operations,
            },
        },
        executor,
    )
    assert batch["status"] == "succeeded", batch
    assert batch["execution_summary"]["failed_operations"] == 0

    tree = executor.execute(
        OperationRequest(
            id=f"inspect_generated_{item['id']}",
            type="geometry_nodes.inspect_tree",
            target={"object_id": object_id, "modifier_id": "BlendeX Geometry"},
            params={},
        )
    )
    labels = {node.get("label", "") for node in tree["nodes"]}
    for node in plan["graph"]["nodes"]:
        assert node["label"] in labels, (node["label"], labels)
    assert len(tree["links"]) >= max(1, len(plan["graph"]["links"]) - 1), tree["links"]

    undo = undo_last_batch()
    assert undo["undo_status"] == "undone", undo


def run_generated_graph_smoke(executor):
    for item in load_heldout_prompts()[:2]:
        _execute_generated_graph(executor, item)


def main():
    blendex.register()
    try:
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object

        executor = GeometryNodesExecutor(SmokeContext())
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

        tree_after_undo = executor.execute(
            OperationRequest(
                id="smoke_tree_after_undo",
                type="geometry_nodes.inspect_tree",
                target={"object_id": obj.name, "modifier_id": "BlendeX Geometry"},
                params={},
            )
        )
        labels_after_undo = {node.get("label") for node in tree_after_undo["nodes"]}
        assert "Smoke Batch Join" not in labels_after_undo

        _execute_recipe(
            executor,
            "architecture.grid_tower",
            {"levels": 2, "columns": 2},
            {"Grid Tower", "Tower Level 1", "Tower Level 2"},
            minimum_links=2,
        )
        _execute_recipe(
            executor,
            "scatter.ground_points",
            {"density": 5, "seed": 2},
            {"Ground Points", "Ground Random", "Ground Density Random"},
            minimum_links=1,
        )
        if os.environ.get("BLENDEX_GENERATED_GRAPH_SMOKE"):
            run_generated_graph_smoke(executor)
    finally:
        blendex.unregister()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
