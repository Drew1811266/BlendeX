from typing import Any, Dict, List, Optional


def _error(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = {"code": code, "message": message}
    if details:
        result["details"] = details
    return result


def _nodes_by_id(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for node in graph.get("nodes", []) if isinstance(node, dict) and "id" in node}


def _socket_by_name(capability: Dict[str, Any], direction: str, socket_name: str) -> Optional[Dict[str, Any]]:
    for socket in capability.get("inputs" if direction == "input" else "outputs", []):
        if socket_name in (socket.get("name"), socket.get("identifier")):
            return socket
    return None


def _dynamic_group_input_socket(graph: Dict[str, Any], socket_name: str) -> Optional[Dict[str, Any]]:
    for socket in graph.get("group_inputs", []):
        if socket_name in (socket.get("name"), socket.get("identifier")):
            return {
                "name": socket.get("name"),
                "identifier": socket.get("identifier"),
                "socket_type": socket.get("socket_type", ""),
                "is_field": False,
            }
    return None


def _capability_for_node(
    capabilities: Optional[Dict[str, Any]],
    node: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not isinstance(capabilities, dict):
        return None
    node_types = capabilities.get("node_types")
    if not isinstance(node_types, dict):
        return None
    return node_types.get(node.get("node_type"))


def _validate_unique_node_ids(graph: Dict[str, Any], errors: List[Dict[str, Any]]) -> None:
    seen = set()
    for node in graph.get("nodes", []):
        node_id = node.get("id")
        if node_id in seen:
            errors.append(_error("DUPLICATE_NODE_ID", f"Duplicate graph node id: {node_id}"))
        seen.add(node_id)


def _validate_group_output(graph: Dict[str, Any], nodes_by_id: Dict[str, Dict[str, Any]], errors: List[Dict[str, Any]]) -> None:
    output_nodes = [node for node in graph.get("nodes", []) if node.get("node_type") == "NodeGroupOutput"]
    if not output_nodes:
        errors.append(_error("MISSING_GROUP_OUTPUT", "Graph must include a NodeGroupOutput node."))
        return
    output_ids = {node["id"] for node in output_nodes}
    has_geometry_link = any(
        link.get("to_node") in output_ids and link.get("to_socket") == "Geometry"
        for link in graph.get("links", [])
    )
    if not has_geometry_link:
        errors.append(_error("MISSING_FINAL_GEOMETRY_LINK", "Group Output must receive final Geometry."))


def _validate_link_nodes(graph: Dict[str, Any], nodes_by_id: Dict[str, Dict[str, Any]], errors: List[Dict[str, Any]]) -> None:
    for link in graph.get("links", []):
        missing = [
            node_id
            for node_id in (link.get("from_node"), link.get("to_node"))
            if node_id not in nodes_by_id
        ]
        if missing:
            errors.append(
                _error(
                    "UNKNOWN_LINK_NODE",
                    f"Link references unknown node: {', '.join(missing)}",
                    {"link": link},
                )
            )


def _validate_capability_links(
    graph: Dict[str, Any],
    capabilities: Optional[Dict[str, Any]],
    nodes_by_id: Dict[str, Dict[str, Any]],
    errors: List[Dict[str, Any]],
) -> None:
    for link in graph.get("links", []):
        from_node = nodes_by_id.get(link.get("from_node"))
        to_node = nodes_by_id.get(link.get("to_node"))
        if from_node is None or to_node is None:
            continue
        from_capability = _capability_for_node(capabilities, from_node)
        to_capability = _capability_for_node(capabilities, to_node)
        if from_capability is None or to_capability is None:
            continue
        from_socket = _socket_by_name(from_capability, "output", link.get("from_socket"))
        if from_socket is None and from_node.get("node_type") == "NodeGroupInput":
            from_socket = _dynamic_group_input_socket(graph, link.get("from_socket"))
        to_socket = _socket_by_name(to_capability, "input", link.get("to_socket"))
        if from_socket is None or to_socket is None:
            errors.append(_error("UNKNOWN_SOCKET", "Link references an unknown socket.", {"link": link}))
            continue
        from_type = from_socket.get("socket_type", "")
        to_type = to_socket.get("socket_type", "")
        if from_type and to_type and from_type != to_type:
            errors.append(
                _error(
                    "SOCKET_TYPE_MISMATCH",
                    f"Cannot link {from_type} to {to_type}.",
                    {"link": link},
                )
            )
        if from_socket.get("is_field") and not to_socket.get("is_field"):
            errors.append(
                _error(
                    "FIELD_VALUE_MISMATCH",
                    "A field output cannot feed a non-field value socket.",
                    {"link": link},
                )
            )


def _validate_instance_realization(
    graph: Dict[str, Any],
    nodes_by_id: Dict[str, Dict[str, Any]],
    errors: List[Dict[str, Any]],
) -> None:
    for link in graph.get("links", []):
        from_node = nodes_by_id.get(link.get("from_node"))
        to_node = nodes_by_id.get(link.get("to_node"))
        if from_node is None or to_node is None:
            continue
        if (
            from_node.get("node_type") == "GeometryNodeInstanceOnPoints"
            and link.get("from_socket") == "Instances"
            and to_node.get("node_type") == "GeometryNodeSetPosition"
        ):
            errors.append(
                _error(
                    "INSTANCE_REQUIRES_REALIZE",
                    "Instances must be realized before per-element position edits.",
                    {"link": link},
                )
            )


def validate_graph(graph: Dict[str, Any], capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    nodes_by_id = _nodes_by_id(graph)
    _validate_unique_node_ids(graph, errors)
    _validate_group_output(graph, nodes_by_id, errors)
    _validate_link_nodes(graph, nodes_by_id, errors)
    _validate_capability_links(graph, capabilities, nodes_by_id, errors)
    _validate_instance_realization(graph, nodes_by_id, errors)
    return {"valid": not errors, "errors": errors, "warnings": warnings}
