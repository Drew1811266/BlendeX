import copy
from typing import Any, Dict, List, Optional

from .graph_ir import add_link, add_node
from .graph_validation import validate_graph


def _node_by_id(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for node in graph.get("nodes", []) if isinstance(node, dict)}


def _has_node(graph: Dict[str, Any], node_id: str) -> bool:
    return node_id in _node_by_id(graph)


def _unique_node_id(graph: Dict[str, Any], base: str) -> str:
    if not _has_node(graph, base):
        return base
    index = 1
    while _has_node(graph, f"{base}_{index}"):
        index += 1
    return f"{base}_{index}"


def _geometry_output_socket(node_type: str) -> str:
    if node_type in {"GeometryNodeMeshCube", "GeometryNodeMeshLine", "GeometryNodeMeshGrid"}:
        return "Mesh"
    if node_type == "GeometryNodeInstanceOnPoints":
        return "Instances"
    if node_type == "GeometryNodeDistributePointsOnFaces":
        return "Points"
    return "Geometry"


def _last_geometry_source(graph: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for node in reversed(graph.get("nodes", [])):
        if node.get("node_type") != "NodeGroupOutput":
            return node
    return None


def _ensure_group_output(graph: Dict[str, Any], repairs: List[Dict[str, Any]]) -> bool:
    changed = False
    nodes = graph.setdefault("nodes", [])
    output = next((node for node in nodes if node.get("node_type") == "NodeGroupOutput"), None)
    if output is None:
        output = add_node(graph, "group_output", "NodeGroupOutput", label="Output", location=[520, 0])
        repairs.append({"code": "ADD_GROUP_OUTPUT", "message": "Added missing NodeGroupOutput."})
        changed = True
    has_final_link = any(
        link.get("to_node") == output["id"] and link.get("to_socket") == "Geometry"
        for link in graph.get("links", [])
    )
    if not has_final_link:
        source = _last_geometry_source(graph)
        if source is not None and source["id"] != output["id"]:
            add_link(graph, source["id"], _geometry_output_socket(source["node_type"]), output["id"], "Geometry")
            repairs.append(
                {
                    "code": "ADD_FINAL_GEOMETRY_LINK",
                    "message": "Connected the last geometry source to Group Output.",
                }
            )
            changed = True
    return changed


def _capability_for_node(capabilities: Optional[Dict[str, Any]], node_type: str) -> Optional[Dict[str, Any]]:
    if not isinstance(capabilities, dict):
        return None
    node_types = capabilities.get("node_types")
    if not isinstance(node_types, dict):
        return None
    return node_types.get(node_type)


def _canonical_socket_name(capability: Dict[str, Any], direction: str, socket_name: str) -> Optional[str]:
    sockets = capability.get("outputs" if direction == "output" else "inputs", [])
    normalized = socket_name.casefold().replace(" ", "")
    for socket in sockets:
        for key in ("name", "identifier"):
            candidate = str(socket.get(key, ""))
            if candidate.casefold().replace(" ", "") == normalized:
                return candidate
    return None


def _normalize_socket_names(
    graph: Dict[str, Any],
    capabilities: Optional[Dict[str, Any]],
    repairs: List[Dict[str, Any]],
) -> bool:
    changed = False
    nodes = _node_by_id(graph)
    for link in graph.get("links", []):
        from_node = nodes.get(link.get("from_node"))
        to_node = nodes.get(link.get("to_node"))
        if from_node is None or to_node is None:
            continue
        from_capability = _capability_for_node(capabilities, from_node.get("node_type"))
        to_capability = _capability_for_node(capabilities, to_node.get("node_type"))
        if from_capability is not None:
            canonical = _canonical_socket_name(from_capability, "output", link.get("from_socket", ""))
            if canonical and canonical != link.get("from_socket"):
                link["from_socket"] = canonical
                repairs.append({"code": "NORMALIZE_SOCKET_NAME", "message": "Normalized source socket name."})
                changed = True
        if to_capability is not None:
            canonical = _canonical_socket_name(to_capability, "input", link.get("to_socket", ""))
            if canonical and canonical != link.get("to_socket"):
                link["to_socket"] = canonical
                repairs.append({"code": "NORMALIZE_SOCKET_NAME", "message": "Normalized target socket name."})
                changed = True
    return changed


def _insert_realize_instances(graph: Dict[str, Any], repairs: List[Dict[str, Any]]) -> bool:
    changed = False
    nodes = _node_by_id(graph)
    new_links = []
    for link in graph.get("links", []):
        from_node = nodes.get(link.get("from_node"))
        to_node = nodes.get(link.get("to_node"))
        if (
            from_node is not None
            and to_node is not None
            and from_node.get("node_type") == "GeometryNodeInstanceOnPoints"
            and link.get("from_socket") == "Instances"
            and to_node.get("node_type") == "GeometryNodeSetPosition"
            and link.get("to_socket") == "Geometry"
        ):
            realize_id = _unique_node_id(graph, "realize_instances")
            add_node(graph, realize_id, "GeometryNodeRealizeInstances", label="Realize Instances", location=[0, 0])
            new_links.append(
                {"from_node": from_node["id"], "from_socket": "Instances", "to_node": realize_id, "to_socket": "Geometry"}
            )
            new_links.append(
                {"from_node": realize_id, "from_socket": "Geometry", "to_node": to_node["id"], "to_socket": "Geometry"}
            )
            repairs.append(
                {
                    "code": "INSERT_REALIZE_INSTANCES",
                    "message": "Inserted Realize Instances before Set Position.",
                }
            )
            changed = True
        else:
            new_links.append(link)
    if changed:
        graph["links"] = new_links
    return changed


def repair_graph(
    graph: Dict[str, Any],
    capabilities: Optional[Dict[str, Any]] = None,
    *,
    max_passes: int = 3,
) -> Dict[str, Any]:
    repaired_graph = copy.deepcopy(graph)
    repairs: List[Dict[str, Any]] = []
    validation = validate_graph(repaired_graph, capabilities)
    for _ in range(max_passes):
        if validation["valid"]:
            break
        changed = False
        changed = _normalize_socket_names(repaired_graph, capabilities, repairs) or changed
        changed = _insert_realize_instances(repaired_graph, repairs) or changed
        changed = _ensure_group_output(repaired_graph, repairs) or changed
        validation = validate_graph(repaired_graph, capabilities)
        if not changed:
            break
    return {
        "graph": repaired_graph,
        "validation": validation,
        "repairs": repairs,
        "repaired": bool(repairs),
    }
