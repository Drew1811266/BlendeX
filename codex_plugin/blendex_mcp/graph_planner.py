from typing import Any, Dict, Optional, Set

from .effect_model import parse_effect_intent
from .graph_ir import add_group_input, add_link, add_node, graph_to_operations, new_graph, set_socket_value
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


def _prompt_has(intent: Dict[str, Any], *needles: str) -> bool:
    prompt = intent.get("normalized_prompt", "")
    return any(needle in prompt for needle in needles)


def _build_scatter_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Scatter")
    effects = set(intent.get("effects", []))
    add_node(graph, "group_input", "NodeGroupInput", label="Input Surface", location=[-560, 0], effects=["source"])
    add_node(graph, "scatter_points", "GeometryNodeDistributePointsOnFaces", label="Distribute Points", location=[-340, 0], effects=["scatter", "field"])
    add_node(graph, "instance_source", "GeometryNodeMeshCube", label="Generated Instance Source", location=[-340, -220], effects=["source"])
    add_node(graph, "instance_on_points", "GeometryNodeInstanceOnPoints", label="Instance on Points", location=[-100, 0], effects=["instance", "scatter"])
    add_node(graph, "realize_instances", "GeometryNodeRealizeInstances", label="Realize Instances", location=[160, 0], effects=["realize"])
    set_socket_value(graph, "scatter_points", "Density", intent.get("parameters", {}).get("density", 24.0))
    add_link(graph, "group_input", "Geometry", "scatter_points", "Mesh")
    if "selection" in effects or _prompt_has(intent, "only where", "center", "edges", "density attribute"):
        add_node(graph, "scatter_mask", "FunctionNodeCompare", label="Scatter Selection Mask", location=[-560, 220], effects=["selection", "field"])
        add_link(graph, "scatter_mask", "Result", "scatter_points", "Selection")
    add_link(graph, "scatter_points", "Points", "instance_on_points", "Points")
    add_link(graph, "instance_source", "Mesh", "instance_on_points", "Instance")
    add_link(graph, "instance_on_points", "Instances", "realize_instances", "Geometry")
    final_node = "realize_instances"
    if "attribute" in effects:
        add_node(graph, "store_scatter_attribute", "GeometryNodeStoreNamedAttribute", label="Store Scatter Attribute", location=[360, 0], effects=["attribute", "field"])
        set_socket_value(graph, "store_scatter_attribute", "Name", "scatter_density")
        add_link(graph, "realize_instances", "Geometry", "store_scatter_attribute", "Geometry")
        final_node = "store_scatter_attribute"
    _add_output_chain(graph, final_node)
    graph["explanations"].append(
        "Semantic scatter plan: distribute points on source geometry, instance generated geometry, then realize instances."
    )
    return graph


def _build_material_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Material")
    effects = set(intent.get("effects", []))
    add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-620, 0], effects=["source"])
    geometry_source = "group_input"
    if "attribute" in effects:
        add_node(graph, "store_selection_attribute", "GeometryNodeStoreNamedAttribute", label="Store Selection Attribute", location=[-360, 0], effects=["attribute", "field"])
        set_socket_value(graph, "store_selection_attribute", "Name", "selection_mask")
        add_link(graph, "group_input", "Geometry", "store_selection_attribute", "Geometry")
        geometry_source = "store_selection_attribute"
    if "selection" in effects or "field" in effects:
        field_node_type = "GeometryNodeInputNormal" if _prompt_has(intent, "slope", "steep", "flat") else "GeometryNodeInputPosition"
        field_node_id = "normal_field" if field_node_type == "GeometryNodeInputNormal" else "position_field"
        field_socket = "Normal" if field_node_type == "GeometryNodeInputNormal" else "Position"
        add_node(graph, field_node_id, field_node_type, label="Selection Field Source", location=[-620, 220], effects=["field", "selection"])
        add_node(graph, "separate_axis", "ShaderNodeSeparateXYZ", label="Extract Field Axis", location=[-400, 220], effects=["field", "selection"])
        add_node(graph, "selection_mask", "FunctionNodeCompare", label="Selection Mask", location=[-180, 220], effects=["field", "selection"])
        set_socket_value(graph, "selection_mask", "B", 0.5)
        add_link(graph, field_node_id, field_socket, "separate_axis", "Vector")
        add_link(graph, "separate_axis", "Z", "selection_mask", "A")
    add_node(graph, "set_material", "GeometryNodeSetMaterial", label="Set Material", location=[80, 0], effects=["material", "selection"])
    add_link(graph, geometry_source, "Geometry", "set_material", "Geometry")
    if "selection" in effects or "field" in effects:
        add_link(graph, "selection_mask", "Result", "set_material", "Selection")
    _add_output_chain(graph, "set_material")
    graph["explanations"].append(
        "Semantic material plan: derive a field selection mask when needed, then assign material to the selected geometry."
    )
    return graph


def _build_attribute_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Attribute")
    add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-680, 0], effects=["source"])
    add_node(graph, "position_field", "GeometryNodeInputPosition", label="Position Field", location=[-680, 220], effects=["field", "attribute"])
    add_node(graph, "capture_attribute", "GeometryNodeCaptureAttribute", label="Capture Attribute", location=[-420, 0], effects=["attribute", "field"])
    add_node(graph, "set_position", "GeometryNodeSetPosition", label="Set Position", location=[-140, 0], effects=["deform", "field"])
    add_link(graph, "group_input", "Geometry", "capture_attribute", "Geometry")
    add_link(graph, "position_field", "Position", "capture_attribute", "Value")
    add_link(graph, "capture_attribute", "Geometry", "set_position", "Geometry")
    add_link(graph, "position_field", "Position", "set_position", "Offset")
    _add_output_chain(graph, "set_position")
    graph["explanations"].append(
        "Semantic attribute plan: capture a field before deformation, then continue geometry flow through Set Position."
    )
    return graph


def _build_deform_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Deform")
    effects = set(intent.get("effects", []))
    if _prompt_has(intent, "terrain", "grid"):
        add_node(graph, "grid_source", "GeometryNodeMeshGrid", label="Terrain Grid", location=[-680, 0], effects=["source", "deform", "field"])
        geometry_source = ("grid_source", "Mesh")
    else:
        add_node(graph, "group_input", "NodeGroupInput", label="Input Geometry", location=[-680, 0], effects=["source"])
        geometry_source = ("group_input", "Geometry")
    add_node(graph, "position_field", "GeometryNodeInputPosition", label="Position Field", location=[-680, 220], effects=["field", "attribute"])
    if "attribute" in effects:
        add_node(graph, "capture_attribute", "GeometryNodeCaptureAttribute", label="Capture Deform Attribute", location=[-420, 0], effects=["attribute", "field"])
        add_link(graph, geometry_source[0], geometry_source[1], "capture_attribute", "Geometry")
        add_link(graph, "position_field", "Position", "capture_attribute", "Value")
        geometry_source = ("capture_attribute", "Geometry")
    add_node(graph, "set_position", "GeometryNodeSetPosition", label="Set Position", location=[-120, 0], effects=["deform", "field"])
    add_link(graph, geometry_source[0], geometry_source[1], "set_position", "Geometry")
    add_link(graph, "position_field", "Position", "set_position", "Offset")
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
    add_node(graph, "module_deform", "GeometryNodeSetPosition", label="Module Variation", location=[180, 0], effects=["deform", "field", "architecture"])
    add_link(graph, "module_points", "Mesh", "instance_modules", "Points")
    add_link(graph, "module_source", "Mesh", "instance_modules", "Instance")
    add_link(graph, "instance_modules", "Instances", "realize_modules", "Geometry")
    add_link(graph, "realize_modules", "Geometry", "module_deform", "Geometry")
    _add_output_chain(graph, "module_deform")
    graph["explanations"].append(
        "Semantic architecture plan: create procedural module positions, instance a generated module, then realize the result."
    )
    return graph


def _build_attribute_architecture_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = _build_architecture_graph(intent)
    output_link = next(link for link in graph["links"] if link["to_node"] == "group_output")
    graph["links"].remove(output_link)
    add_node(graph, "floor_index", "GeometryNodeInputIndex", label="Floor Index Field", location=[120, 220], effects=["field", "attribute"])
    add_node(graph, "store_floor_index", "GeometryNodeStoreNamedAttribute", label="Store Floor Index", location=[360, 0], effects=["attribute", "field", "architecture"])
    set_socket_value(graph, "store_floor_index", "Name", "floor_index")
    add_link(graph, output_link["from_node"], output_link["from_socket"], "store_floor_index", "Geometry")
    add_link(graph, "floor_index", "Index", "store_floor_index", "Value")
    add_link(graph, "store_floor_index", "Geometry", "group_output", "Geometry")
    graph["explanations"].append("Stored a generated floor index attribute for downstream shading.")
    return graph


def _build_exposed_architecture_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Exposed Floors")
    add_group_input(graph, "Floor Count", "NodeSocketInt", 8, identifier="floor_count")
    add_node(graph, "group_input", "NodeGroupInput", label="Exposed Controls", location=[-760, 160], effects=["source", "attribute", "field"])
    add_node(graph, "module_points", "GeometryNodeMeshLine", label="Floor Positions", location=[-520, 0], effects=["source", "architecture", "field"])
    add_node(graph, "module_source", "GeometryNodeMeshCube", label="Floor Module", location=[-520, -220], effects=["source", "architecture"])
    add_node(graph, "instance_modules", "GeometryNodeInstanceOnPoints", label="Repeat Floors", location=[-260, 0], effects=["instance", "architecture"])
    add_node(graph, "realize_modules", "GeometryNodeRealizeInstances", label="Realize Floors", location=[0, 0], effects=["realize"])
    add_link(graph, "group_input", "Floor Count", "module_points", "Count")
    add_link(graph, "module_points", "Mesh", "instance_modules", "Points")
    add_link(graph, "module_source", "Mesh", "instance_modules", "Instance")
    add_link(graph, "instance_modules", "Instances", "realize_modules", "Geometry")
    _add_output_chain(graph, "realize_modules")
    graph["explanations"].append("Exposed Floor Count as a group input and connected it to the procedural floor generator.")
    return graph


def _build_material_variation_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Material Variation")
    add_node(graph, "module_points", "GeometryNodeMeshLine", label="Module Positions", location=[-760, 0], effects=["source", "instance"])
    add_node(graph, "module_source", "GeometryNodeMeshCube", label="Window Module", location=[-760, -220], effects=["source", "architecture"])
    add_node(graph, "instance_modules", "GeometryNodeInstanceOnPoints", label="Repeat Window Modules", location=[-500, 0], effects=["instance", "architecture"])
    add_node(graph, "realize_modules", "GeometryNodeRealizeInstances", label="Realize Window Modules", location=[-260, 0], effects=["realize"])
    add_node(graph, "random_variation", "FunctionNodeRandomValue", label="Random Material Variation", location=[-260, 220], effects=["field", "attribute"])
    add_node(graph, "store_material_variation", "GeometryNodeStoreNamedAttribute", label="Store Material Variation", location=[0, 0], effects=["attribute", "material"])
    add_node(graph, "set_material", "GeometryNodeSetMaterial", label="Assign Varied Material", location=[260, 0], effects=["material", "selection"])
    set_socket_value(graph, "store_material_variation", "Name", "material_variation")
    set_socket_value(graph, "random_variation", "Seed", intent.get("parameters", {}).get("seed", 7))
    add_link(graph, "module_points", "Mesh", "instance_modules", "Points")
    add_link(graph, "module_source", "Mesh", "instance_modules", "Instance")
    add_link(graph, "instance_modules", "Instances", "realize_modules", "Geometry")
    add_link(graph, "realize_modules", "Geometry", "store_material_variation", "Geometry")
    add_link(graph, "random_variation", "Value", "store_material_variation", "Value")
    add_link(graph, "store_material_variation", "Geometry", "set_material", "Geometry")
    _add_output_chain(graph, "set_material")
    graph["explanations"].append("Stored random material variation as a named attribute before assigning material.")
    return graph


def _build_instance_selection_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Instance Selection")
    add_node(graph, "grid_points", "GeometryNodeMeshGrid", label="Grid Points", location=[-760, 0], effects=["source", "field"])
    add_node(graph, "module_source", "GeometryNodeMeshCube", label="Instance Module", location=[-760, -220], effects=["source"])
    add_node(graph, "index_field", "GeometryNodeInputIndex", label="Index Field", location=[-520, 220], effects=["field", "selection"])
    add_node(graph, "selection_mask", "FunctionNodeCompare", label="Every Other Selection", location=[-300, 220], effects=["field", "selection"])
    add_node(graph, "instance_modules", "GeometryNodeInstanceOnPoints", label="Instance on Selected Points", location=[-300, 0], effects=["instance", "selection"])
    add_node(graph, "realize_modules", "GeometryNodeRealizeInstances", label="Realize Selected Instances", location=[-40, 0], effects=["realize"])
    set_socket_value(graph, "selection_mask", "B", 0)
    add_link(graph, "grid_points", "Mesh", "instance_modules", "Points")
    add_link(graph, "module_source", "Mesh", "instance_modules", "Instance")
    add_link(graph, "index_field", "Index", "selection_mask", "A")
    add_link(graph, "selection_mask", "Result", "instance_modules", "Selection")
    add_link(graph, "instance_modules", "Instances", "realize_modules", "Geometry")
    _add_output_chain(graph, "realize_modules")
    graph["explanations"].append("Generated a field selection mask before instancing modules on selected points.")
    return graph


def _build_realized_instance_deform_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Realized Instance Deform")
    add_node(graph, "module_points", "GeometryNodeMeshLine", label="Block Positions", location=[-760, 0], effects=["source", "instance"])
    add_node(graph, "module_source", "GeometryNodeMeshCube", label="Block Module", location=[-760, -220], effects=["source"])
    add_node(graph, "instance_modules", "GeometryNodeInstanceOnPoints", label="Repeat Blocks", location=[-520, 0], effects=["instance"])
    add_node(graph, "realize_modules", "GeometryNodeRealizeInstances", label="Realize Blocks", location=[-280, 0], effects=["realize", "instance"])
    add_node(graph, "random_block_id", "FunctionNodeRandomValue", label="Block Attribute Field", location=[-280, 220], effects=["field", "attribute"])
    add_node(graph, "store_block_attribute", "GeometryNodeStoreNamedAttribute", label="Store Block Attribute", location=[-40, 0], effects=["attribute", "field"])
    add_node(graph, "set_position", "GeometryNodeSetPosition", label="Mesh-Only Edit", location=[200, 0], effects=["deform", "field"])
    set_socket_value(graph, "store_block_attribute", "Name", "block_variation")
    add_link(graph, "module_points", "Mesh", "instance_modules", "Points")
    add_link(graph, "module_source", "Mesh", "instance_modules", "Instance")
    add_link(graph, "instance_modules", "Instances", "realize_modules", "Geometry")
    add_link(graph, "realize_modules", "Geometry", "set_position", "Geometry")
    add_link(graph, "random_block_id", "Value", "store_block_attribute", "Value")
    add_link(graph, "set_position", "Geometry", "store_block_attribute", "Geometry")
    _add_output_chain(graph, "store_block_attribute")
    graph["explanations"].append("Realized instances before applying a mesh-only deformation and storing per-block data.")
    return graph


def _build_pavilion_graph(intent: Dict[str, Any]) -> Dict[str, Any]:
    graph = new_graph("BlendeX Semantic Pavilion")
    add_node(graph, "column_points", "GeometryNodeMeshLine", label="Radial Column Positions", location=[-760, 0], effects=["source", "architecture", "field"])
    add_node(graph, "column_source", "GeometryNodeMeshCube", label="Column Module", location=[-760, -220], effects=["source", "architecture"])
    add_node(graph, "instance_columns", "GeometryNodeInstanceOnPoints", label="Instance Columns", location=[-500, 0], effects=["instance", "architecture"])
    add_node(graph, "realize_columns", "GeometryNodeRealizeInstances", label="Realize Columns", location=[-260, 0], effects=["realize"])
    add_node(graph, "roof_ring", "GeometryNodeMeshCube", label="Roof Ring", location=[-260, -220], effects=["architecture"])
    add_node(graph, "join_pavilion", "GeometryNodeJoinGeometry", label="Join Pavilion Parts", location=[40, 0], effects=["architecture", "field"])
    add_link(graph, "column_points", "Mesh", "instance_columns", "Points")
    add_link(graph, "column_source", "Mesh", "instance_columns", "Instance")
    add_link(graph, "instance_columns", "Instances", "realize_columns", "Geometry")
    add_link(graph, "realize_columns", "Geometry", "join_pavilion", "Geometry")
    add_link(graph, "roof_ring", "Mesh", "join_pavilion", "Geometry")
    _add_output_chain(graph, "join_pavilion")
    graph["explanations"].append("Composed a pavilion from instanced columns and a joined roof ring.")
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
    if _prompt_has(intent, "exposed parameter", "node group", "floor count"):
        return _build_exposed_architecture_graph(intent)
    if _prompt_has(intent, "pavilion", "roof ring", "around a circle"):
        return _build_pavilion_graph(intent)
    if "architecture" in effects and "attribute" in effects:
        return _build_attribute_architecture_graph(intent)
    if "material" in effects and "instance" in effects and "attribute" in effects:
        return _build_material_variation_graph(intent)
    if primary == "material" or "material" in effects:
        return _build_material_graph(intent)
    if "scatter" in effects:
        return _build_scatter_graph(intent)
    if "instance" in effects and "deform" in effects:
        return _build_realized_instance_deform_graph(intent)
    if "instance" in effects and ("selection" in effects or "field" in effects):
        return _build_instance_selection_graph(intent)
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
