from typing import Any, Dict, List, Optional, Set

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request

from .capabilities import IMPLEMENTED_OPERATIONS


def _operation_id(operation: Any, index: int) -> str:
    if isinstance(operation, dict):
        operation_id = operation.get("id")
        if isinstance(operation_id, str) and operation_id:
            return operation_id
    return f"op_{index}"


def _operation_type(operation: Any) -> str:
    if isinstance(operation, dict):
        operation_type = operation.get("type")
        if isinstance(operation_type, str):
            return operation_type
    return ""


def _status_for(results: List[Dict[str, Any]], warnings: Optional[List[Dict[str, Any]]] = None) -> str:
    if warnings:
        return "partial"
    ok_count = sum(1 for entry in results if entry["ok"])
    if ok_count == len(results):
        return "valid"
    if ok_count == 0:
        return "invalid"
    return "partial"


def _validate_request_runtime(request: OperationRequest, executor: Any) -> None:
    if request.type not in IMPLEMENTED_OPERATIONS:
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Operation is not implemented by this BlendeX runtime: {request.type}",
            retry_hint="Call capabilities.supported_operations before planning a batch.",
        )
    validator = getattr(executor, "validate", None)
    if request.type.startswith("geometry_nodes.") and callable(validator):
        validator(request)


def _validate_one(operation: Dict[str, Any], index: int, executor: Any) -> Dict[str, Any]:
    result, _warning = _validate_one_with_simulation(operation, index, executor, set(), set())
    return result


def validate_operations(operations: List[Dict[str, Any]], executor: Any) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    simulated_modifiers: Set[tuple[str, str]] = set()
    simulated_nodes: Set[str] = set()
    for index, operation in enumerate(operations):
        result, warning = _validate_one_with_simulation(
            operation,
            index,
            executor,
            simulated_modifiers,
            simulated_nodes,
        )
        results.append(result)
        if result["ok"] and isinstance(operation, dict):
            _record_simulated_modifier(operation, simulated_modifiers)
            _record_simulated_node(operation, simulated_nodes)
        if warning:
            warning = dict(warning)
            warning["operation_id"] = result["id"]
            warnings.append(warning)
    response = {"status": _status_for(results, warnings), "operations": results}
    if warnings:
        response["warnings"] = warnings
    return response


def _preview_for(operation: Dict[str, Any]) -> Dict[str, Any]:
    operation_type = operation.get("type")
    target = operation.get("target", {})
    params = operation.get("params", {})
    if operation_type == "scene.create_carrier_mesh":
        return {"section": "objects", "name": params.get("name", "BlendeX Carrier")}
    if operation_type == "geometry_nodes.create_modifier":
        return {
            "section": "modifiers",
            "object_id": target.get("object_id"),
            "modifier_id": params.get("modifier_id", "BlendeX Geometry"),
        }
    if operation_type == "geometry_nodes.create_node":
        node_type = params.get("node_type")
        return {
            "section": "nodes",
            "object_id": target.get("object_id"),
            "modifier_id": target.get("modifier_id", "BlendeX Geometry"),
            "node_type": node_type,
            "client_id": params.get("client_id"),
            "label": params.get("label", node_type),
        }
    if operation_type == "geometry_nodes.set_socket_value":
        return {
            "section": "socket_values",
            "node_id": params.get("node_id"),
            "socket": params.get("socket"),
            "value": params.get("value"),
        }
    if operation_type == "geometry_nodes.link_sockets":
        return {
            "section": "links",
            "from_node": params.get("from_node"),
            "from_socket": params.get("from_socket"),
            "to_node": params.get("to_node"),
            "to_socket": params.get("to_socket"),
        }
    if operation_type == "geometry_nodes.label_node":
        return {"section": "labels", "node_id": params.get("node_id"), "label": params.get("label")}
    return {"section": "warnings", "code": "NO_PREVIEW", "message": f"No preview section for {operation_type}"}


def _empty_preview() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "objects": [],
        "modifiers": [],
        "nodes": [],
        "socket_values": [],
        "links": [],
        "labels": [],
        "warnings": [],
    }


def _preview_target(preview: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    for key in ("modifiers", "nodes"):
        values = preview.get(key, [])
        if not values:
            continue
        first = values[0]
        object_id = first.get("object_id") if isinstance(first, dict) else None
        modifier_id = first.get("modifier_id") if isinstance(first, dict) else None
        return {
            "object_id": object_id if isinstance(object_id, str) and object_id else "selected target",
            "modifier_id": modifier_id if isinstance(modifier_id, str) and modifier_id else "BlendeX Geometry",
        }
    objects = preview.get("objects", [])
    if objects and isinstance(objects[0], dict):
        name = objects[0].get("name")
        if isinstance(name, str) and name:
            return {"object_id": name, "modifier_id": "BlendeX Geometry"}
    return {"object_id": "selected target", "modifier_id": "BlendeX Geometry"}


def _preview_summary(
    status: str,
    operations: List[Dict[str, Any]],
    preview: Dict[str, List[Dict[str, Any]]],
    warnings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "status": status,
        "requires_confirmation": status in {"valid", "partial"},
        "operation_count": len(operations),
        "target": _preview_target(preview),
        "changes": {
            "objects": len(preview.get("objects", [])),
            "modifiers": len(preview.get("modifiers", [])),
            "nodes": len(preview.get("nodes", [])),
            "socket_values": len(preview.get("socket_values", [])),
            "links": len(preview.get("links", [])),
            "labels": len(preview.get("labels", [])),
        },
        "warnings": len(warnings),
    }


def _record_preview(operation: Dict[str, Any], preview: Dict[str, List[Dict[str, Any]]]) -> None:
    item = _preview_for(operation)
    section = item.pop("section")
    preview.setdefault(section, []).append(item)


def _record_simulated_node(operation: Dict[str, Any], simulated_nodes: Set[str]) -> None:
    if operation.get("type") != "geometry_nodes.create_node":
        return
    params = operation.get("params", {})
    client_id = params.get("client_id")
    if isinstance(client_id, str) and client_id:
        simulated_nodes.add(client_id)


def _operation_modifier_key(operation: Dict[str, Any]) -> Optional[tuple[str, str]]:
    target = operation.get("target", {})
    params = operation.get("params", {})
    object_id = target.get("object_id")
    if operation.get("type") == "geometry_nodes.create_modifier":
        modifier_id = params.get("modifier_id", "BlendeX Geometry")
    else:
        modifier_id = target.get("modifier_id", "BlendeX Geometry")
    if isinstance(object_id, str) and object_id and isinstance(modifier_id, str) and modifier_id:
        return object_id, modifier_id
    return None


def _request_modifier_key(request: OperationRequest) -> Optional[tuple[str, str]]:
    if not request.type.startswith("geometry_nodes."):
        return None
    object_id = request.target.get("object_id")
    if request.type == "geometry_nodes.create_modifier":
        modifier_id = request.params.get("modifier_id", "BlendeX Geometry")
    else:
        modifier_id = request.target.get("modifier_id", "BlendeX Geometry")
    if isinstance(object_id, str) and object_id and isinstance(modifier_id, str) and modifier_id:
        return object_id, modifier_id
    return None


def _record_simulated_modifier(operation: Dict[str, Any], simulated_modifiers: Set[tuple[str, str]]) -> None:
    if operation.get("type") != "geometry_nodes.create_modifier":
        return
    key = _operation_modifier_key(operation)
    if key is not None:
        simulated_modifiers.add(key)


def _simulated_references(operation: Dict[str, Any], simulated_nodes: Set[str]) -> Set[str]:
    params = operation.get("params", {})
    references = (
        params.get("from_node"),
        params.get("to_node"),
        params.get("node_id"),
    )
    return {reference for reference in references if isinstance(reference, str) and reference in simulated_nodes}


def _simulation_warning(operation: Dict[str, Any], references: Set[str]) -> Dict[str, Any]:
    return {
        "code": "SIMULATED_NODE_METADATA",
        "operation_id": _operation_id(operation, 0),
        "node_ids": sorted(references),
        "message": "Dry run simulated a node created earlier in the batch; runtime socket metadata is partial.",
    }


def _modifier_simulation_warning(key: tuple[str, str]) -> Dict[str, Any]:
    object_id, modifier_id = key
    return {
        "code": "SIMULATED_MODIFIER",
        "object_id": object_id,
        "modifier_id": modifier_id,
        "message": "Dry run simulated a modifier created earlier in the batch; runtime node tree metadata is partial.",
    }


def _error_mentions_reference(error: BlendexError, references: Set[str]) -> bool:
    return any(reference in error.message for reference in references)


def _can_treat_simulated_error_as_partial(request: OperationRequest, references: Set[str]) -> bool:
    if not references:
        return False
    if request.type == "geometry_nodes.link_sockets":
        # The executor validates source node/socket before destination node/socket. A simulated
        # source node can hide real destination-side errors, so only treat simulated destination
        # node failures as partial dry-run metadata.
        to_node = request.params.get("to_node")
        return isinstance(to_node, str) and references == {to_node}
    if request.type in {"geometry_nodes.set_socket_value", "geometry_nodes.label_node"}:
        node_id = request.params.get("node_id")
        return isinstance(node_id, str) and references == {node_id}
    return False


def _dry_run_one(
    operation: Dict[str, Any],
    index: int,
    executor: Any,
    simulated_modifiers: Set[tuple[str, str]],
    simulated_nodes: Set[str],
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    return _validate_one_with_simulation(operation, index, executor, simulated_modifiers, simulated_nodes)


def _validate_one_with_simulation(
    operation: Dict[str, Any],
    index: int,
    executor: Any,
    simulated_modifiers: Set[tuple[str, str]],
    simulated_nodes: Set[str],
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    try:
        request = OperationRequest.from_dict(operation)
        validate_request(request)
        references = _simulated_references(operation, simulated_nodes)
        modifier_key = _request_modifier_key(request)
        try:
            _validate_request_runtime(request, executor)
        except BlendexError as error:
            if (
                error.code == "MODIFIER_NOT_FOUND"
                and modifier_key is not None
                and modifier_key in simulated_modifiers
                and modifier_key[1] in error.message
            ):
                return (
                    {"index": index, "id": request.id, "type": request.type, "ok": True, "message": "OK"},
                    _modifier_simulation_warning(modifier_key),
                )
            if (
                references
                and error.code in {"NODE_TYPE_NOT_FOUND", "SOCKET_NOT_FOUND"}
                and _error_mentions_reference(error, references)
                and _can_treat_simulated_error_as_partial(request, references)
            ):
                return (
                    {"index": index, "id": request.id, "type": request.type, "ok": True, "message": "OK"},
                    _simulation_warning(operation, references),
                )
            raise
        warning = _simulation_warning(operation, references) if references else None
        return {"index": index, "id": request.id, "type": request.type, "ok": True, "message": "OK"}, warning
    except BlendexError as error:
        return (
            {
                "index": index,
                "id": _operation_id(operation, index),
                "type": _operation_type(operation),
                "ok": False,
                "error": error.to_dict(),
            },
            None,
        )


def dry_run_operations(operations: List[Dict[str, Any]], executor: Any) -> Dict[str, Any]:
    preview = _empty_preview()
    results: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    simulated_modifiers: Set[tuple[str, str]] = set()
    simulated_nodes: Set[str] = set()
    for index, operation in enumerate(operations):
        result, warning = _dry_run_one(operation, index, executor, simulated_modifiers, simulated_nodes)
        results.append(result)
        if result["ok"] and isinstance(operation, dict):
            _record_preview(operation, preview)
            _record_simulated_modifier(operation, simulated_modifiers)
            _record_simulated_node(operation, simulated_nodes)
        if warning:
            warning = dict(warning)
            warning["operation_id"] = result["id"]
            warnings.append(warning)
            preview["warnings"].append(warning)
    status = _status_for(results, warnings)
    return {
        "status": status,
        "operations": results,
        "preview": preview,
        "summary": _preview_summary(status, operations, preview, warnings),
        "warnings": warnings,
    }
