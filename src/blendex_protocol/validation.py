import math
from typing import Any, Set

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
    "safety.execute_batch",
    "safety.batch_history",
    "safety.inspect_batch",
    "safety.undo_last_batch",
    "safety.check_ownership",
}

MAX_JSON_VALUE_DEPTH = 100


def _require_string(mapping, key: str, message: str) -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise BlendexError("VALIDATION_FAILED", message)


def _require_value_key(mapping, key: str, message: str) -> None:
    if key not in mapping:
        raise BlendexError("VALIDATION_FAILED", message)


def _number_matches(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value.bit_length() <= 53
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _require_number_pair(mapping, key: str, message: str) -> None:
    if key not in mapping:
        return
    value = mapping.get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise BlendexError("VALIDATION_FAILED", message)
    if not all(_number_matches(item) for item in value):
        raise BlendexError("VALIDATION_FAILED", message)


def _json_value_matches(value: Any, depth: int = 0) -> bool:
    if depth > MAX_JSON_VALUE_DEPTH:
        return False
    if isinstance(value, bool) or isinstance(value, str) or value is None:
        return True
    if isinstance(value, (int, float)):
        return _number_matches(value)
    if isinstance(value, list):
        return all(_json_value_matches(item, depth + 1) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _json_value_matches(item, depth + 1)
            for key, item in value.items()
        )
    return False


def _require_json_value(value: Any, message: str) -> None:
    if not _json_value_matches(value):
        raise BlendexError("VALIDATION_FAILED", message)


def _require_operations(params) -> None:
    operations = params.get("operations")
    if not isinstance(operations, list):
        raise BlendexError("VALIDATION_FAILED", "Batch operations must be an array.")
    if not operations:
        raise BlendexError("VALIDATION_FAILED", "Batch operations must contain at least one operation.")
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise BlendexError(
                "VALIDATION_FAILED",
                f"Batch operation at index {index} must be an object.",
            )
        target = operation.get("target", {})
        params_value = operation.get("params", {})
        if not isinstance(target, dict):
            raise BlendexError(
                "VALIDATION_FAILED",
                f"Batch operation at index {index} target must be an object.",
            )
        if not isinstance(params_value, dict):
            raise BlendexError(
                "VALIDATION_FAILED",
                f"Batch operation at index {index} params must be an object.",
            )
        _require_json_value(
            target,
            f"Batch operation at index {index} target contains invalid JSON value.",
        )
        _require_json_value(
            params_value,
            f"Batch operation at index {index} params contains invalid JSON value.",
        )


def _require_optional_summary(params) -> None:
    if "summary" not in params:
        return
    summary = params.get("summary")
    if not isinstance(summary, str) or not summary:
        raise BlendexError("VALIDATION_FAILED", "Batch summary must be a non-empty string.")


def _require_no_params(params, message: str) -> None:
    if params:
        raise BlendexError("VALIDATION_FAILED", message)


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
    if request.type == "geometry_nodes.create_modifier" and "modifier_id" in request.params:
        _require_string(
            request.params,
            "modifier_id",
            "create_modifier params.modifier_id must be a non-empty string.",
        )
    if request.type == "geometry_nodes.create_node":
        node_type = request.params.get("node_type")
        if not isinstance(node_type, str) or not node_type:
            raise BlendexError(
                "VALIDATION_FAILED",
                "create_node requires params.node_type.",
                retry_hint="Use a node type returned by capabilities.scan.",
            )
        _require_number_pair(
            request.params,
            "location",
                "create_node params.location must be an array of two finite numbers.",
        )
        if "label" in request.params:
            _require_string(
                request.params,
                "label",
                "create_node params.label must be a non-empty string.",
            )
    if request.type == "scene.create_carrier_mesh" and "name" in request.params:
        _require_string(
            request.params,
            "name",
            "create_carrier_mesh params.name must be a non-empty string.",
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
        _require_json_value(
            request.params.get("value"),
            "set_socket_value params.value contains invalid JSON value.",
        )
    if request.type == "geometry_nodes.label_node":
        _require_string(request.params, "node_id", "label_node requires params.node_id.")
        _require_string(request.params, "label", "label_node requires params.label.")
    if request.type == "geometry_nodes.mark_ownership":
        _require_string(request.target, "object_id", "mark_ownership requires target.object_id.")
    if request.type in {"safety.validate_batch", "safety.dry_run", "safety.execute_batch"}:
        _require_operations(request.params)
    if request.type == "safety.execute_batch":
        _require_optional_summary(request.params)
    if request.type == "safety.inspect_batch":
        _require_string(request.params, "batch_id", "inspect_batch requires params.batch_id.")
    if request.type == "safety.undo_last_batch":
        _require_no_params(request.params, "undo_last_batch does not accept params.")
