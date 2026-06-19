from typing import Any, Dict, List, Optional

from .graph_recipe import (
    DEFAULT_MODIFIER_NAME,
    GraphLinkSpec,
    GraphNodeSpec,
    GraphRecipeBatch,
    GraphSocketValueSpec,
)


def new_graph(object_name: str, modifier_name: str = DEFAULT_MODIFIER_NAME) -> Dict[str, Any]:
    if not isinstance(object_name, str) or not object_name.strip():
        raise ValueError("Graph object_name must be a non-empty string")
    if not isinstance(modifier_name, str) or not modifier_name.strip():
        raise ValueError("Graph modifier_name must be a non-empty string")
    return {
        "object_name": object_name,
        "modifier_name": modifier_name,
        "group_inputs": [],
        "nodes": [],
        "socket_values": [],
        "links": [],
        "explanations": [],
    }


def add_node(
    graph: Dict[str, Any],
    node_id: str,
    node_type: str,
    *,
    label: Optional[str] = None,
    location: Optional[List[float]] = None,
    effects: Optional[List[str]] = None,
) -> Dict[str, Any]:
    node = {
        "id": node_id,
        "node_type": node_type,
        "label": label or node_type,
        "location": list(location or [0, 0]),
        "effects": list(effects or []),
    }
    graph.setdefault("nodes", []).append(node)
    return node


def add_group_input(
    graph: Dict[str, Any],
    name: str,
    socket_type: str,
    default_value: Any = None,
    *,
    identifier: Optional[str] = None,
) -> Dict[str, Any]:
    group_input = {
        "name": name,
        "identifier": identifier or name.lower().replace(" ", "_"),
        "socket_type": socket_type,
        "default_value": default_value,
    }
    graph.setdefault("group_inputs", []).append(group_input)
    return group_input


def set_socket_value(graph: Dict[str, Any], node_id: str, socket: str, value: Any) -> Dict[str, Any]:
    socket_value = {"node_id": node_id, "socket": socket, "value": value}
    graph.setdefault("socket_values", []).append(socket_value)
    return socket_value


def add_link(
    graph: Dict[str, Any],
    from_node: str,
    from_socket: str,
    to_node: str,
    to_socket: str,
) -> Dict[str, str]:
    link = {
        "from_node": from_node,
        "from_socket": from_socket,
        "to_node": to_node,
        "to_socket": to_socket,
    }
    graph.setdefault("links", []).append(link)
    return link


def graph_to_operations(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    batch = GraphRecipeBatch(
        object_name=graph["object_name"],
        modifier_name=graph.get("modifier_name", DEFAULT_MODIFIER_NAME),
        nodes=[
            GraphNodeSpec(
                node["id"],
                node["node_type"],
                node.get("label") or node["node_type"],
                list(node.get("location", [0, 0])),
            )
            for node in graph.get("nodes", [])
        ],
        socket_values=[
            GraphSocketValueSpec(value["node_id"], value["socket"], value.get("value"))
            for value in graph.get("socket_values", [])
        ],
        links=[
            GraphLinkSpec(
                link["from_node"],
                link["from_socket"],
                link["to_node"],
                link["to_socket"],
            )
            for link in graph.get("links", [])
        ],
    )
    return batch.to_operations()
