from typing import Any, Dict, Optional, Set

from .effect_model import parse_effect_intent
from .graph_ir import add_link, add_node, graph_to_operations, new_graph, set_socket_value
from .graph_repair import repair_graph
from .graph_validation import validate_graph
from .node_semantics import nodes_for_effect


def _unsupported(message: str, retry_hint: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    error = {
        "code": "PLANNER_UNSUPPORTED_REQUEST",
        "message": message,
        "retry_hint": retry_hint,
    }
    if details is not None:
        error["details"] = details
    return {"mode": "unsupported", "error": error}


def _available_node_types(capabilities: Optional[Dict[str, Any]]) -> Optional[Set[str]]:
    if not isinstance(capabilities, dict):
        return None
    node_types = capabilities.get("node_types")
    if not isinstance(node_types, dict) or not node_types:
        return None
    return set(node_types)


def _capabilities_for_validation(capabilities: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return capabilities if _available_node_types(capabilities) is not None else None


def _add_output_chain(graph: Dict[str, Any], from_node: str, from_socket: str = "Geometry") -> None:
    add_node(graph, "group_output", "NodeGroupOutput", label="Output", location=[520, 0])
    add_link(graph, from_node, from_socket, "group_output", "Geometry")


def _build_scatter_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Scatter")
    add_node(graph, "group_input", "NodeGroupInput", label="Input Surface", location=[-560, 0], effects=["source"])
    add_node(graph, "scatter_points", "GeometryNodeDistributePointsOnFaces", label="Distribute Points", location=[-340, 0], effects=["scatter", "field"])
    add_node(graph, "instance_source", "GeometryNodeMeshCube", label="Generated Instance Source", location=[-340, -220], effects=["source"])
    add_node(graph, "instance_on_points", "GeometryNodeInstanceOnPoints", label="Instance on Points", location=[-100, 0], effects=["instance", "scatter"])
    add_node(graph, "realize_instances", "GeometryNodeRealizeInstances", label="Realize Instances", location=[160, 0], effects=["realize"])
    set_socket_value(graph, "scatter_points", "Density", intent.get("parameters", {}).get("density", 24.0))
    add_link(graph, "group_input", "Geometry", "scatter_points", "Mesh")
    add_link(graph, "scatter_points", "Points", "instance_on_points", "Points")
    add_link(graph, "instance_source", "Mesh", "instance_on_points", "Instance")
    add_link(graph, "instance_on_points", "Instances", "realize_instances", "Geometry")
    _add_output_chain(graph, "realize_instances")
    graph["explanations"].append(
        "Semantic scatter plan: distribute points on source geometry, instance generated geometry, then realize instances."
    )
    return graph


def _build_material_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Material")
    add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-360, 0], effects=["source"])
    add_node(graph, "set_material", "GeometryNodeSetMaterial", label="Set Material", location=[-120, 0], effects=["material", "selection"])
    add_link(graph, "group_input", "Geometry", "set_material", "Geometry")
    _add_output_chain(graph, "set_material")
    graph["explanations"].append(
        "Semantic material plan: pass source geometry through Set Material so selection fields can be added later."
    )
    return graph


def _build_attribute_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Attribute")
    add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-560, 0], effects=["source"])
    add_node(graph, "capture_attribute", "GeometryNodeCaptureAttribute", label="Capture Attribute", location=[-320, 0], effects=["attribute", "field"])
    add_node(graph, "set_position", "GeometryNodeSetPosition", label="Set Position", location=[-80, 0], effects=["deform", "field"])
    add_link(graph, "group_input", "Geometry", "capture_attribute", "Geometry")
    add_link(graph, "capture_attribute", "Geometry", "set_position", "Geometry")
    _add_output_chain(graph, "set_position")
    graph["explanations"].append(
        "Semantic attribute plan: capture a field before deformation, then continue geometry flow through Set Position."
    )
    return graph


def _build_deform_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Deform")
    add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-360, 0], effects=["source"])
    add_node(graph, "set_position", "GeometryNodeSetPosition", label="Set Position", location=[-120, 0], effects=["deform", "field"])
    add_link(graph, "group_input", "Geometry", "set_position", "Geometry")
    _add_output_chain(graph, "set_position")
    graph["explanations"].append(
        "Semantic deformation plan: use Set Position as the data-flow node that evaluates field-driven offsets."
    )
    return graph


def _build_architecture_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Architecture")
    add_node(graph, "module_points", "GeometryNodeMeshLine", label="Module Positions", location=[-560, 0], effects=["source", "architecture"])
    add_node(graph, "module_source", "GeometryNodeMeshCube", label="Module Source", location=[-560, -220], effects=["source", "architecture"])
    add_node(graph, "instance_modules", "GeometryNodeInstanceOnPoints", label="Repeat Modules", location=[-300, 0], effects=["instance", "architecture"])
    add_node(graph, "realize_modules", "GeometryNodeRealizeInstances", label="Realize Modules", location=[-60, 0], effects=["realize"])
    add_link(graph, "module_points", "Mesh", "instance_modules", "Points")
    add_link(graph, "module_source", "Mesh", "instance_modules", "Instance")
    add_link(graph, "instance_modules", "Instances", "realize_modules", "Geometry")
    _add_output_chain(graph, "realize_modules")
    graph["explanations"].append(
        "Semantic architecture plan: create procedural module positions, instance a generated module, then realize the result."
    )
    return graph


def _build_passthrough_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Graph")
    add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-220, 0], effects=["source"])
    _add_output_chain(graph, "group_input")
    graph["explanations"].append("Semantic fallback plan: preserve source geometry while keeping a valid graph.")
    return graph


def _graph_for_intent(intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    primary = intent.get("primary_effect")
    effects = set(intent.get("effects", []))
    if primary == "scatter":
        return _build_scatter_graph(intent)
    if primary == "material":
        return _build_material_graph(intent)
    if primary == "attribute":
        return _build_attribute_graph(intent)
    if primary == "architecture":
        return _build_architecture_graph(intent)
    if primary == "deform" or "deform" in effects:
        return _build_deform_graph(intent)
    if effects & {"field", "selection", "instance"}:
        return _build_passthrough_graph(intent)
    return None


def _missing_node_types(graph: Dict[str, Any], capabilities: Optional[Dict[str, Any]]) -> list:
    available = _available_node_types(capabilities)
    if available is None:
        return []
    required = {node["node_type"] for node in graph.get("nodes", [])}
    return sorted(required - available)


def plan_graph(prompt: str, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    intent = parse_effect_intent(prompt)
    if intent["unsupported_reasons"]:
        return _unsupported(
            "BlendeX cannot synthesize this procedural graph within the v0.5 scope.",
            "Ask for architecture, scattering, instancing, deformation, fields, attributes, selection, or material assignment.",
            {"unsupported_reasons": intent["unsupported_reasons"], "intent": intent},
        )
    graph = _graph_for_intent(intent)
    if graph is None:
        return _unsupported(
            "BlendeX cannot infer a supported procedural graph from this request yet.",
            "Describe the desired procedural effect, such as scatter, deform, instance, material, or attribute.",
            {"intent": intent},
        )
    missing_node_types = _missing_node_types(graph, capabilities)
    if missing_node_types:
        return _unsupported(
            f"BlendeX cannot synthesize this graph; missing node types: {', '.join(missing_node_types)}.",
            "Refresh Blender capabilities or simplify the request.",
            {"missing_node_types": missing_node_types, "intent": intent},
        )
    validation_capabilities = _capabilities_for_validation(capabilities)
    repairs = []
    validation = validate_graph(graph, validation_capabilities)
    if not validation["valid"]:
        repair_result = repair_graph(graph, validation_capabilities)
        graph = repair_result["graph"]
        validation = repair_result["validation"]
        repairs = repair_result["repairs"]
    if not validation["valid"]:
        return _unsupported(
            "BlendeX generated a graph candidate but static validation rejected it.",
            "Try a simpler procedural request or refresh Blender capabilities.",
            {"validation": validation, "repairs": repairs, "intent": intent},
        )
    semantic_candidates = {
        effect: nodes_for_effect(effect)
        for effect in intent.get("effects", [])
        if nodes_for_effect(effect)
    }
    return {
        "mode": "graph_plan",
        "label": "Semantic Geometry Nodes graph",
        "intent": intent,
        "graph": graph,
        "node_types": [node["node_type"] for node in graph.get("nodes", [])],
        "operations": graph_to_operations(graph),
        "validation": validation,
        "repairs": repairs,
        "semantic_candidates": semantic_candidates,
        "explanation": "Semantic graph planner selected nodes by effect intent and validated the graph IR.",
        "message": "Synthesized semantic Geometry Nodes graph plan.",
    }
