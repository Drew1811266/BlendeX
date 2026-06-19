import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


DEFAULT_MODIFIER_NAME = "BlendeX Geometry"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "item"


@dataclass
class GraphNodeSpec:
    client_id: str
    node_type: str
    label: str
    location: List[float]


@dataclass
class GraphSocketValueSpec:
    node_id: str
    socket: str
    value: Any


@dataclass
class GraphLinkSpec:
    from_node: str
    from_socket: str
    to_node: str
    to_socket: str


@dataclass
class GraphRecipeBatch:
    object_name: str
    nodes: List[GraphNodeSpec] = field(default_factory=list)
    socket_values: List[GraphSocketValueSpec] = field(default_factory=list)
    links: List[GraphLinkSpec] = field(default_factory=list)
    modifier_name: str = DEFAULT_MODIFIER_NAME

    def to_operations(self) -> List[Dict[str, Any]]:
        operations: List[Dict[str, Any]] = [
            {
                "id": f"create_{_slug(self.object_name)}",
                "type": "scene.create_carrier_mesh",
                "target": {},
                "params": {"name": self.object_name},
            },
            {
                "id": "create_modifier",
                "type": "geometry_nodes.create_modifier",
                "target": {"object_id": self.object_name},
                "params": {"modifier_id": self.modifier_name},
            },
        ]
        operations.extend(self._node_operations())
        operations.extend(self._socket_value_operations())
        operations.extend(self._link_operations())
        return operations

    def _node_operations(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": f"create_{_slug(node.client_id)}",
                "type": "geometry_nodes.create_node",
                "target": {
                    "object_id": self.object_name,
                    "modifier_id": self.modifier_name,
                },
                "params": {
                    "node_type": node.node_type,
                    "label": node.label,
                    "client_id": node.client_id,
                    "location": list(node.location),
                },
            }
            for node in self.nodes
        ]

    def _socket_value_operations(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": f"set_{_slug(value.node_id)}_{_slug(value.socket)}",
                "type": "geometry_nodes.set_socket_value",
                "target": {
                    "object_id": self.object_name,
                    "modifier_id": self.modifier_name,
                },
                "params": {
                    "node_id": value.node_id,
                    "socket": value.socket,
                    "value": value.value,
                },
            }
            for value in self.socket_values
        ]

    def _link_operations(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": (
                    f"link_{_slug(link.from_node)}_{_slug(link.from_socket)}"
                    f"_to_{_slug(link.to_node)}_{_slug(link.to_socket)}"
                ),
                "type": "geometry_nodes.link_sockets",
                "target": {
                    "object_id": self.object_name,
                    "modifier_id": self.modifier_name,
                },
                "params": {
                    "from_node": link.from_node,
                    "from_socket": link.from_socket,
                    "to_node": link.to_node,
                    "to_socket": link.to_socket,
                },
            }
            for link in self.links
        ]
