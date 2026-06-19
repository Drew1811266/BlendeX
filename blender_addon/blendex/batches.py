import copy
import secrets
from typing import Any, Callable, Dict, List, Optional, Set, Union

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request

from .history import BatchRecord
from .scene import create_carrier_mesh
from .state import STATE


_REFERENCE_PARAM_KEYS = ("node_id", "from_node", "to_node")
_UNSUPPORTED_UNDO = object()
_MUTATING_OPERATION_TYPES = {
    "scene.create_carrier_mesh",
    "geometry_nodes.create_modifier",
    "geometry_nodes.create_node",
    "geometry_nodes.link_sockets",
    "geometry_nodes.set_socket_value",
    "geometry_nodes.label_node",
    "geometry_nodes.mark_ownership",
}
_CREATED_SUMMARY_KEYS = {
    "scene.create_carrier_mesh": "objects",
    "geometry_nodes.create_modifier": "modifiers",
    "geometry_nodes.create_node": "nodes",
    "geometry_nodes.link_sockets": "links",
    "geometry_nodes.set_socket_value": "socket_values",
    "geometry_nodes.label_node": "labels",
}


def _batch_id() -> str:
    return f"batch_{secrets.token_hex(8)}"


def _request_from_operation(operation: Dict[str, Any], index: int) -> OperationRequest:
    payload = {
        "id": operation.get("id", f"op_{index}"),
        "type": operation.get("type", ""),
        "target": operation.get("target", {}),
        "params": copy.deepcopy(operation.get("params", {})),
    }
    request = OperationRequest.from_dict(payload)
    validate_request(request)
    return request


def _declared_client_ids(operations: List[Dict[str, Any]]) -> Set[str]:
    client_ids: Set[str] = set()
    for index, operation in enumerate(operations):
        if operation.get("type") != "geometry_nodes.create_node":
            continue
        params = operation.get("params", {})
        client_id = params.get("client_id")
        if not isinstance(client_id, str) or not client_id:
            continue
        if client_id in client_ids:
            raise BlendexError(
                "VALIDATION_FAILED",
                f"Duplicate batch client_id at operation index {index}: {client_id}",
            )
        client_ids.add(client_id)
    return client_ids


def _resolve_references(
    request: OperationRequest,
    client_nodes: Dict[str, str],
    declared_client_ids: Set[str],
) -> OperationRequest:
    params = copy.deepcopy(request.params)
    for key in _REFERENCE_PARAM_KEYS:
        value = params.get(key)
        if not isinstance(value, str):
            continue
        if value in client_nodes:
            params[key] = client_nodes[value]
        elif value in declared_client_ids:
            raise BlendexError(
                "EXECUTION_FAILED",
                f"Client node reference was not resolved: {value}",
            )
    return OperationRequest(
        id=request.id,
        type=request.type,
        target=copy.deepcopy(request.target),
        params=params,
    )


def _record_created_node(request: OperationRequest, result: Dict[str, Any], client_nodes: Dict[str, str]) -> None:
    if request.type != "geometry_nodes.create_node":
        return
    client_id = request.params.get("client_id")
    node_id = result.get("node_id") or result.get("id")
    if isinstance(client_id, str) and client_id and isinstance(node_id, str) and node_id:
        client_nodes[client_id] = node_id


def _status_for(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "succeeded"
    ok_count = sum(1 for result in results if result["ok"])
    if ok_count == len(results):
        return "succeeded"
    if ok_count == 0:
        return "failed"
    return "partial"


def _first_error(results: List[Dict[str, Any]]) -> Union[Dict[str, Any], None]:
    for result in results:
        error = result.get("error")
        if isinstance(error, dict):
            return error
    return None


def _request_payload(request: OperationRequest) -> Dict[str, Any]:
    return request.to_dict()


def _execute_operation(request: OperationRequest, executor: Any) -> Dict[str, Any]:
    if request.type == "scene.create_carrier_mesh":
        context = getattr(executor, "context", None)
        if context is not None:
            return create_carrier_mesh(context, request.params.get("name", "BlendeX Carrier"))
    return executor.execute(request)


def _collection_get(executor: Any, collection: Any, key: str) -> Any:
    getter = getattr(executor, "_collection_get", None)
    if callable(getter):
        return getter(collection, key)
    if collection is None:
        return None
    if isinstance(collection, dict):
        return collection.get(key)
    collection_get = getattr(collection, "get", None)
    if callable(collection_get):
        try:
            return collection_get(key)
        except Exception:
            return None
    try:
        iterator = iter(collection)
    except TypeError:
        return None
    for item in iterator:
        if getattr(item, "name", None) == key or getattr(item, "identifier", None) == key:
            return item
        if isinstance(item, dict) and (item.get("id") == key or item.get("name") == key):
            return item
    return None


def _executor_object(executor: Any, object_id: str) -> Any:
    object_getter = getattr(executor, "_object", None)
    if callable(object_getter):
        return object_getter(object_id)
    context = getattr(executor, "context", None)
    obj = _collection_get(executor, getattr(context, "objects", None), object_id)
    if obj is None:
        raise BlendexError("OBJECT_NOT_FOUND", f"Object not found: {object_id}")
    return obj


def _executor_modifier(executor: Any, obj: Any, modifier_id: str) -> Any:
    modifier_getter = getattr(executor, "_modifier", None)
    if callable(modifier_getter):
        return modifier_getter(obj, modifier_id)
    modifier = _collection_get(executor, getattr(obj, "modifiers", None), modifier_id)
    if modifier is None:
        raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier not found: {modifier_id}")
    return modifier


def _executor_tree(executor: Any, modifier: Any) -> Any:
    tree_getter = getattr(executor, "_existing_node_tree", None)
    if callable(tree_getter):
        return tree_getter(modifier)
    tree = getattr(modifier, "node_group", None)
    if isinstance(modifier, dict):
        tree = modifier.get("node_group")
    if tree is None:
        raise BlendexError("NODE_TREE_NOT_FOUND", "Modifier has no Geometry Nodes tree.")
    return tree


def _executor_node(executor: Any, tree: Any, node_id: str) -> Any:
    node_getter = getattr(executor, "_node", None)
    if callable(node_getter):
        return node_getter(tree, node_id)
    node = _collection_get(executor, getattr(tree, "nodes", None), node_id)
    if node is None:
        raise BlendexError("NODE_TYPE_NOT_FOUND", f"Node not found: {node_id}")
    return node


def _remove_collection_item(collection: Any, key: str, item: Any, label: str) -> None:
    remover = getattr(collection, "remove", None)
    if callable(remover):
        try:
            remover(item)
            return
        except TypeError:
            remover(item, do_unlink=True)
            return
    if isinstance(collection, dict):
        if key in collection:
            del collection[key]
            return
        for existing_key, existing_item in list(collection.items()):
            if existing_item is item:
                del collection[existing_key]
                return
            if isinstance(existing_item, dict) and (
                existing_item.get("id") == key or existing_item.get("name") == key
            ):
                del collection[existing_key]
                return
        raise BlendexError("UNDO_UNAVAILABLE", f"Could not remove {label}: {key}")
    created = getattr(collection, "created", None)
    if isinstance(created, list):
        if item in created:
            created.remove(item)
            return
        for existing in list(created):
            if getattr(existing, "name", None) == key or getattr(existing, "identifier", None) == key:
                created.remove(existing)
                return
    raise BlendexError("UNDO_UNAVAILABLE", f"Could not remove {label}: {key}")


def _remove_object_from_context(executor: Any, object_id: str) -> None:
    context = getattr(executor, "context", None)
    obj = _collection_get(executor, getattr(context, "objects", None), object_id)
    if obj is None:
        return
    bpy_module = getattr(context, "_bpy", None)
    data_objects = getattr(getattr(bpy_module, "data", None), "objects", None)
    if data_objects is not None:
        remover = getattr(data_objects, "remove", None)
        if callable(remover):
            remover(obj, do_unlink=True)
            return
    _remove_collection_item(getattr(context, "objects", None), object_id, obj, "object")


def _undo_step_before_request(request: OperationRequest, executor: Any) -> Any:
    if request.type == "geometry_nodes.create_node":
        context = getattr(executor, "context", None)
        if context is None:
            return _UNSUPPORTED_UNDO
        obj = _executor_object(executor, request.target["object_id"])
        _executor_modifier(executor, obj, request.target.get("modifier_id", "BlendeX Geometry"))
        return {
            "action": "remove_node",
            "object_id": request.target["object_id"],
            "modifier_id": request.target.get("modifier_id", "BlendeX Geometry"),
        }
    if request.type == "geometry_nodes.create_modifier":
        context = getattr(executor, "context", None)
        if context is None:
            return _UNSUPPORTED_UNDO
        obj = _executor_object(executor, request.target["object_id"])
        modifier_id = request.params.get("modifier_id", "BlendeX Geometry")
        if _collection_get(executor, getattr(obj, "modifiers", None), modifier_id) is not None:
            return _UNSUPPORTED_UNDO
        return {
            "action": "remove_modifier",
            "object_id": request.target["object_id"],
            "modifier_id": modifier_id,
        }
    if request.type == "scene.create_carrier_mesh":
        context = getattr(executor, "context", None)
        object_id = request.params.get("name", "BlendeX Carrier")
        if context is None or _collection_get(executor, getattr(context, "objects", None), object_id) is not None:
            return _UNSUPPORTED_UNDO
        return {"action": "remove_object", "object_id": object_id}
    if request.type in _MUTATING_OPERATION_TYPES:
        return _UNSUPPORTED_UNDO
    return None


def _complete_undo_step(undo_step: Any, result: Dict[str, Any]) -> Any:
    if undo_step is _UNSUPPORTED_UNDO or undo_step is None:
        return undo_step
    step = dict(undo_step)
    action = step.get("action")
    if action == "remove_node":
        node_id = result.get("node_id") or result.get("id")
        if not isinstance(node_id, str) or not node_id:
            return _UNSUPPORTED_UNDO
        step["node_id"] = node_id
    elif action == "remove_modifier":
        modifier_id = result.get("modifier_id") or step.get("modifier_id")
        if not isinstance(modifier_id, str) or not modifier_id:
            return _UNSUPPORTED_UNDO
        step["modifier_id"] = modifier_id
    elif action == "remove_object":
        object_id = result.get("object_id") or result.get("name") or step.get("object_id")
        if not isinstance(object_id, str) or not object_id:
            return _UNSUPPORTED_UNDO
        step["object_id"] = object_id
    return step


def _apply_undo_step(executor: Any, step: Dict[str, Any]) -> None:
    action = step["action"]
    if action == "remove_node":
        obj = _executor_object(executor, step["object_id"])
        modifier = _executor_modifier(executor, obj, step["modifier_id"])
        tree = _executor_tree(executor, modifier)
        node = _executor_node(executor, tree, step["node_id"])
        _remove_collection_item(getattr(tree, "nodes", None), step["node_id"], node, "node")
        return
    if action == "remove_modifier":
        obj = _executor_object(executor, step["object_id"])
        modifier = _executor_modifier(executor, obj, step["modifier_id"])
        _remove_collection_item(getattr(obj, "modifiers", None), step["modifier_id"], modifier, "modifier")
        return
    if action == "remove_object":
        _remove_object_from_context(executor, step["object_id"])
        return
    raise BlendexError("UNDO_UNAVAILABLE", f"Unsupported undo action: {action}")


def _make_undo_callback(
    executor: Any,
    steps: List[Dict[str, Any]],
    unsupported: bool,
    status: str,
) -> Optional[Callable[[BatchRecord], None]]:
    if status != "succeeded" or unsupported or not steps:
        return None

    def undo_batch(_batch: BatchRecord) -> None:
        for step in reversed(steps):
            _apply_undo_step(executor, step)

    return undo_batch


def _batch_preview(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "operations": [
            {
                "id": result["id"],
                "type": result["type"],
                "ok": result["ok"],
            }
            for result in results
        ]
    }


def _created_counts(results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"objects": 0, "modifiers": 0, "nodes": 0, "links": 0, "socket_values": 0, "labels": 0}
    for result in results:
        if not result.get("ok"):
            continue
        key = _CREATED_SUMMARY_KEYS.get(result.get("type"))
        if key is not None:
            counts[key] += 1
    return counts


def _operation_type_counts(results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for result in results:
        operation_type = result.get("type")
        if isinstance(operation_type, str) and operation_type:
            counts[operation_type] = counts.get(operation_type, 0) + 1
    return counts


def _execution_summary(
    status: str,
    results: List[Dict[str, Any]],
    mutation_occurred: bool,
    undo_available: bool,
) -> Dict[str, Any]:
    succeeded = sum(1 for result in results if result.get("ok"))
    return {
        "status": status,
        "operation_count": len(results),
        "succeeded_operations": succeeded,
        "failed_operations": len(results) - succeeded,
        "mutation_occurred": mutation_occurred,
        "undo_available": undo_available,
        "created": _created_counts(results),
        "operation_types": _operation_type_counts(results),
    }


def _operation_error_result(
    index: int,
    operation: Any,
    error: BlendexError,
    mutation_occurred: bool,
    batch_id: str,
) -> Dict[str, Any]:
    error_payload = error.to_dict()
    error_payload["mutation_occurred"] = mutation_occurred
    if mutation_occurred:
        error_payload["batch_id"] = batch_id
    return {
        "index": index,
        "id": operation.get("id", f"op_{index}") if isinstance(operation, dict) else f"op_{index}",
        "type": operation.get("type", "") if isinstance(operation, dict) else "",
        "ok": False,
        "error": error_payload,
    }


def execute_batch(batch: Union[OperationRequest, Dict[str, Any]], executor: Any) -> Dict[str, Any]:
    if executor is None:
        raise BlendexError("BLENDER_NOT_CONNECTED", "Batch execution requires a Blender executor.")
    if isinstance(batch, OperationRequest):
        request = batch
    else:
        request = OperationRequest.from_dict(
            {
                "id": batch.get("id", "batch_request"),
                "type": batch.get("type", "safety.execute_batch"),
                "target": batch.get("target", {}),
                "params": batch.get("params", {}),
            }
        )
    validate_request(request)

    batch_id = _batch_id()
    operations = request.params["operations"]
    dry_run = request.params.get("dry_run", False)
    actor = request.params.get("actor", "")
    confirmation_id = request.params.get("confirmation_id", "")
    results: List[Dict[str, Any]] = []
    undo_steps: List[Dict[str, Any]] = []
    has_unsupported_undo_step = False
    client_nodes: Dict[str, str] = {}
    declared_client_ids = _declared_client_ids(operations)
    mutation_occurred = False

    for index, operation in enumerate(operations):
        try:
            operation_request = _request_from_operation(operation, index)
            resolved_request = _resolve_references(operation_request, client_nodes, declared_client_ids)
            undo_step = _undo_step_before_request(resolved_request, executor)
            result = _execute_operation(resolved_request, executor)
            if not isinstance(result, dict):
                raise BlendexError("EXECUTION_FAILED", "Executor result must be an object.")
            _record_created_node(operation_request, result, client_nodes)
            completed_undo_step = _complete_undo_step(undo_step, result)
            if completed_undo_step is _UNSUPPORTED_UNDO:
                has_unsupported_undo_step = True
            elif isinstance(completed_undo_step, dict):
                undo_steps.append(completed_undo_step)
            results.append(
                {
                    "index": index,
                    "id": resolved_request.id,
                    "type": resolved_request.type,
                    "ok": True,
                    "request": _request_payload(resolved_request),
                    "result": result,
                }
            )
            if resolved_request.type in _MUTATING_OPERATION_TYPES:
                mutation_occurred = True
        except BlendexError as error:
            results.append(_operation_error_result(index, operation, error, mutation_occurred, batch_id))
        except Exception as error:
            blendex_error = BlendexError("EXECUTION_FAILED", str(error) or error.__class__.__name__)
            results.append(_operation_error_result(index, operation, blendex_error, mutation_occurred, batch_id))

    status = _status_for(results)
    error = _first_error(results)
    undo_callback = _make_undo_callback(executor, undo_steps, has_unsupported_undo_step, status)
    record = BatchRecord(
        batch_id=batch_id,
        status=status,
        operation_count=len(operations),
        target=copy.deepcopy(request.target),
        summary=request.params.get("summary", ""),
        confirmation_id=confirmation_id if isinstance(confirmation_id, str) else "",
        dry_run=dry_run if isinstance(dry_run, bool) else False,
        actor=actor if isinstance(actor, str) else "",
        operations=results,
        preview=_batch_preview(results),
        execution_summary=_execution_summary(status, results, mutation_occurred, callable(undo_callback)),
        error=error,
        undo_callback=undo_callback,
    )
    STATE.record_batch(record)
    return record.to_dict()


def undo_last_batch() -> Dict[str, Any]:
    batch = STATE.batch_history.latest()
    if batch is None:
        raise BlendexError("UNDO_UNAVAILABLE", "No BlendeX batch is available to undo.")

    if batch.undo_status == "undone":
        return batch.to_dict()

    if batch.status not in {"succeeded", "partial"}:
        error = BlendexError("UNDO_UNAVAILABLE", "Only applied BlendeX batches can be undone.")
        batch.undo_status = "unavailable"
        batch.undo_error = error.to_dict()
        raise error

    callback = batch.undo_callback
    if not callable(callback):
        error = BlendexError("UNDO_UNAVAILABLE", "No safe BlendeX batch undo is available.")
        batch.undo_status = "unavailable"
        batch.undo_error = error.to_dict()
        raise error

    try:
        callback(batch)
    except BlendexError as error:
        batch.undo_status = "failed"
        batch.undo_error = error.to_dict()
        raise
    except Exception as error:
        blendex_error = BlendexError("UNDO_FAILED", str(error) or error.__class__.__name__)
        batch.undo_status = "failed"
        batch.undo_error = blendex_error.to_dict()
        raise blendex_error

    batch.undo_status = "undone"
    batch.undo_error = None
    return batch.to_dict()
