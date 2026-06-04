from typing import Set

from .errors import BlendexError
from .messages import OperationRequest


ALLOWED_OPERATIONS: Set[str] = {
    "scene.inspect",
    "scene.get_selected_object",
    "scene.create_carrier_mesh",
    "scene.list_modifiers",
    "capabilities.scan",
    "capabilities.supported_operations",
    "geometry_nodes.create_modifier",
    "geometry_nodes.inspect_tree",
    "geometry_nodes.create_node",
    "geometry_nodes.link_sockets",
    "geometry_nodes.set_socket_value",
    "geometry_nodes.label_node",
    "geometry_nodes.mark_ownership",
    "safety.validate_batch",
    "safety.dry_run",
    "safety.undo_last_batch",
    "safety.check_ownership",
}


def _require_string(mapping, key: str, message: str) -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise BlendexError("VALIDATION_FAILED", message)


def _require_value_key(mapping, key: str, message: str) -> None:
    if key not in mapping:
        raise BlendexError("VALIDATION_FAILED", message)


def _require_operations(params) -> None:
    operations = params.get("operations")
    if not isinstance(operations, list):
        raise BlendexError("VALIDATION_FAILED", "Batch operations must be an array.")
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise BlendexError(
                "VALIDATION_FAILED",
                f"Batch operation at index {index} must be an object.",
            )


def validate_request(request: OperationRequest) -> None:
    if request.type not in ALLOWED_OPERATIONS:
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Operation is not allowlisted: {request.type}",
            retry_hint="Choose a supported BlendeX structured operation.",
        )
    if request.type.startswith("geometry_nodes."):
        object_id = request.target.get("object_id")
        if not isinstance(object_id, str) or not object_id:
            raise BlendexError(
                "VALIDATION_FAILED",
                "Geometry Nodes operations require target.object_id.",
                retry_hint="Inspect the scene or create a carrier mesh before editing nodes.",
            )
    if request.type == "geometry_nodes.create_node":
        node_type = request.params.get("node_type")
        if not isinstance(node_type, str) or not node_type:
            raise BlendexError(
                "VALIDATION_FAILED",
                "create_node requires params.node_type.",
                retry_hint="Use a node type returned by capabilities.scan.",
            )
    if request.type == "geometry_nodes.link_sockets":
        _require_string(request.params, "from_node", "link_sockets requires params.from_node.")
        _require_string(request.params, "from_socket", "link_sockets requires params.from_socket.")
        _require_string(request.params, "to_node", "link_sockets requires params.to_node.")
        _require_string(request.params, "to_socket", "link_sockets requires params.to_socket.")
    if request.type == "geometry_nodes.set_socket_value":
        _require_string(request.params, "node_id", "set_socket_value requires params.node_id.")
        _require_string(request.params, "socket", "set_socket_value requires params.socket.")
        _require_value_key(request.params, "value", "set_socket_value requires params.value.")
    if request.type == "geometry_nodes.label_node":
        _require_string(request.params, "node_id", "label_node requires params.node_id.")
        _require_string(request.params, "label", "label_node requires params.label.")
    if request.type == "geometry_nodes.mark_ownership":
        _require_string(request.target, "object_id", "mark_ownership requires target.object_id.")
    if request.type in {"safety.validate_batch", "safety.dry_run"}:
        _require_operations(request.params)
