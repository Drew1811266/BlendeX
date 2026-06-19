import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .graph_planner import plan_graph


ROOT = Path(__file__).resolve().parents[2]
HELDOUT_FIXTURE = ROOT / "docs" / "benchmarks" / "v0-5-heldout-prompts.json"


def _socket(
    name: str,
    socket_type: str = "NodeSocketGeometry",
    direction: str = "input",
    *,
    is_multi_input: bool = False,
    is_field: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "identifier": name,
        "socket_type": socket_type,
        "direction": direction,
        "is_multi_input": is_multi_input,
        "is_field": is_field,
        "default_value": None,
        "enum_items": [],
        "metadata_complete": True,
    }


def _node_capability(inputs: Iterable[Dict[str, Any]], outputs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {"inputs": list(inputs), "outputs": list(outputs), "schema_version": "node_capability.v2"}


def fake_geometry_nodes_capabilities() -> Dict[str, Any]:
    geometry_in = _socket("Geometry", direction="input")
    geometry_out = _socket("Geometry", direction="output")
    mesh_out = _socket("Mesh", direction="output")
    value_field = _socket("Value", "NodeSocketFloat", direction="output", is_field=True)
    vector_field = _socket("Vector", "NodeSocketVector", direction="output", is_field=True)
    bool_field = _socket("Boolean", "NodeSocketBool", direction="output", is_field=True)
    return {
        "schema_version": "node_capability.v2",
        "node_types": {
            "NodeGroupInput": _node_capability([], [geometry_out, _socket("Count", "NodeSocketInt", direction="output")]),
            "NodeGroupOutput": _node_capability([geometry_in], []),
            "GeometryNodeJoinGeometry": _node_capability(
                [_socket("Geometry", is_multi_input=True)],
                [geometry_out],
            ),
            "GeometryNodeTransform": _node_capability([geometry_in], [geometry_out]),
            "GeometryNodeSetPosition": _node_capability(
                [geometry_in, _socket("Selection", "NodeSocketBool", is_field=True), _socket("Offset", "NodeSocketVector", is_field=True)],
                [geometry_out],
            ),
            "GeometryNodeDistributePointsOnFaces": _node_capability(
                [
                    _socket("Mesh"),
                    _socket("Selection", "NodeSocketBool", is_field=True),
                    _socket("Density", "NodeSocketFloat"),
                ],
                [_socket("Points", direction="output")],
            ),
            "GeometryNodeInstanceOnPoints": _node_capability(
                [
                    _socket("Points"),
                    _socket("Instance"),
                    _socket("Selection", "NodeSocketBool", is_field=True),
                    _socket("Scale", "NodeSocketVector", is_field=True),
                ],
                [_socket("Instances", direction="output")],
            ),
            "GeometryNodeRealizeInstances": _node_capability([geometry_in], [geometry_out]),
            "FunctionNodeRandomValue": _node_capability(
                [
                    _socket("Min", "NodeSocketFloat"),
                    _socket("Max", "NodeSocketFloat"),
                    _socket("Seed", "NodeSocketInt"),
                ],
                [value_field],
            ),
            "ShaderNodeSeparateXYZ": _node_capability(
                [_socket("Vector", "NodeSocketVector", is_field=True)],
                [
                    _socket("X", "NodeSocketFloat", direction="output", is_field=True),
                    _socket("Y", "NodeSocketFloat", direction="output", is_field=True),
                    _socket("Z", "NodeSocketFloat", direction="output", is_field=True),
                ],
            ),
            "ShaderNodeMath": _node_capability(
                [_socket("Value", "NodeSocketFloat", is_field=True), _socket("Value_001", "NodeSocketFloat", is_field=True)],
                [value_field],
            ),
            "ShaderNodeVectorMath": _node_capability(
                [_socket("Vector", "NodeSocketVector", is_field=True), _socket("Vector_001", "NodeSocketVector", is_field=True)],
                [vector_field],
            ),
            "FunctionNodeCompare": _node_capability(
                [_socket("A", "", is_field=True), _socket("B", "")],
                [_socket("Result", "NodeSocketBool", direction="output", is_field=True), bool_field],
            ),
            "GeometryNodeCaptureAttribute": _node_capability(
                [geometry_in, _socket("Value", "NodeSocketVector", is_field=True)],
                [geometry_out, _socket("Attribute", "NodeSocketVector", direction="output", is_field=True)],
            ),
            "GeometryNodeStoreNamedAttribute": _node_capability(
                [
                    geometry_in,
                    _socket("Selection", "NodeSocketBool", is_field=True),
                    _socket("Name", "NodeSocketString"),
                    _socket("Value", "", is_field=True),
                ],
                [geometry_out],
            ),
            "GeometryNodeSetMaterial": _node_capability(
                [geometry_in, _socket("Selection", "NodeSocketBool", is_field=True), _socket("Material", "NodeSocketMaterial")],
                [geometry_out],
            ),
            "GeometryNodeInputPosition": _node_capability([], [_socket("Position", "NodeSocketVector", direction="output", is_field=True)]),
            "GeometryNodeInputNormal": _node_capability([], [_socket("Normal", "NodeSocketVector", direction="output", is_field=True)]),
            "GeometryNodeInputIndex": _node_capability([], [_socket("Index", "NodeSocketInt", direction="output", is_field=True)]),
            "GeometryNodeObjectInfo": _node_capability([], [geometry_out]),
            "GeometryNodeCollectionInfo": _node_capability([], [_socket("Instances", direction="output")]),
            "GeometryNodeMeshCube": _node_capability([], [mesh_out]),
            "GeometryNodeMeshLine": _node_capability([_socket("Count", "NodeSocketInt")], [mesh_out]),
            "GeometryNodeMeshGrid": _node_capability(
                [_socket("Vertices X", "NodeSocketInt"), _socket("Vertices Y", "NodeSocketInt")],
                [mesh_out],
            ),
            "GeometryNodeExtrudeMesh": _node_capability([_socket("Mesh")], [mesh_out]),
            "GeometryNodeCurveToMesh": _node_capability([_socket("Curve"), _socket("Profile Curve")], [mesh_out]),
        },
    }


def load_heldout_prompts(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    fixture_path = path or HELDOUT_FIXTURE
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return list(data.get("prompts", []))


def _observed_effects(plan: Dict[str, Any]) -> List[str]:
    effects = set(plan.get("intent", {}).get("effects", []))
    for node in plan.get("graph", {}).get("nodes", []):
        effects.update(node.get("effects", []))
    return sorted(effect for effect in effects if effect != "source")


def _evaluate_prompt(item: Dict[str, Any], capabilities: Dict[str, Any]) -> Dict[str, Any]:
    plan = plan_graph(item["prompt"], capabilities)
    mode = plan.get("mode", "unsupported")
    graph = plan.get("graph", {})
    validation = plan.get("validation", {})
    observed_effects = _observed_effects(plan)
    missing_effects = sorted(set(item.get("expected_effects", [])) - set(observed_effects))
    node_count = len(graph.get("nodes", []))
    meets_minimum_nodes = node_count >= item.get("minimum_nodes", 0)
    valid = mode == "graph_plan" and bool(validation.get("valid"))
    return {
        "id": item["id"],
        "prompt": item["prompt"],
        "mode": mode,
        "valid": valid,
        "used_recipe": mode == "recipe",
        "node_count": node_count,
        "minimum_nodes": item.get("minimum_nodes", 0),
        "meets_minimum_nodes": meets_minimum_nodes,
        "expected_effects": list(item.get("expected_effects", [])),
        "observed_effects": observed_effects,
        "missing_effects": missing_effects,
        "meets_expected_effects": not missing_effects,
        "meets_minimum_properties": valid and meets_minimum_nodes and not missing_effects,
        "validation_errors": list(validation.get("errors", [])),
        "message": plan.get("message") or plan.get("error", {}).get("message", ""),
    }


def _summarize_by_effect(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    by_effect: Dict[str, Dict[str, int]] = {}
    for result in results:
        for effect in result["expected_effects"]:
            bucket = by_effect.setdefault(effect, {"total": 0, "valid": 0, "property_pass": 0})
            bucket["total"] += 1
            if result["valid"]:
                bucket["valid"] += 1
            if result["meets_minimum_properties"]:
                bucket["property_pass"] += 1
    return by_effect


def run_heldout_benchmark(
    *,
    limit: Optional[int] = None,
    capabilities: Optional[Dict[str, Any]] = None,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    prompts = load_heldout_prompts(path)
    if limit is not None:
        prompts = prompts[:limit]
    runtime_capabilities = capabilities or fake_geometry_nodes_capabilities()
    results = [_evaluate_prompt(item, runtime_capabilities) for item in prompts]
    total = len(results)
    return {
        "version": "0.5",
        "total": total,
        "graph_plan_count": sum(1 for result in results if result["mode"] == "graph_plan"),
        "valid_plan_count": sum(1 for result in results if result["valid"]),
        "recipe_count": sum(1 for result in results if result["used_recipe"]),
        "unsupported_count": sum(1 for result in results if result["mode"] == "unsupported"),
        "minimum_node_pass_count": sum(1 for result in results if result["meets_minimum_nodes"]),
        "expected_effect_pass_count": sum(1 for result in results if result["meets_expected_effects"]),
        "property_pass_count": sum(1 for result in results if result["meets_minimum_properties"]),
        "by_effect": _summarize_by_effect(results),
        "results": results,
    }
