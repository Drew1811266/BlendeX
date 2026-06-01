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


def validate_request(request: OperationRequest) -> None:
    if request.type not in ALLOWED_OPERATIONS:
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Operation is not allowlisted: {request.type}",
            retry_hint="Choose a supported BlendeX structured operation.",
        )
    if request.type.startswith("geometry_nodes.") and "object_id" not in request.target:
        raise BlendexError(
            "VALIDATION_FAILED",
            "Geometry Nodes operations require target.object_id.",
            retry_hint="Inspect the scene or create a carrier mesh before editing nodes.",
        )
    if request.type == "geometry_nodes.create_node" and "node_type" not in request.params:
        raise BlendexError(
            "VALIDATION_FAILED",
            "create_node requires params.node_type.",
            retry_hint="Use a node type returned by capabilities.scan.",
        )
