import copy
import secrets
from typing import Any, Dict, List, Set, Union

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request

from .history import BatchRecord
from .state import STATE


_REFERENCE_PARAM_KEYS = ("node_id", "from_node", "to_node")


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


def _operation_error_result(index: int, operation: Any, error: BlendexError) -> Dict[str, Any]:
    return {
        "index": index,
        "id": operation.get("id", f"op_{index}") if isinstance(operation, dict) else f"op_{index}",
        "type": operation.get("type", "") if isinstance(operation, dict) else "",
        "ok": False,
        "error": error.to_dict(),
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
    results: List[Dict[str, Any]] = []
    client_nodes: Dict[str, str] = {}
    declared_client_ids = _declared_client_ids(operations)

    for index, operation in enumerate(operations):
        try:
            operation_request = _request_from_operation(operation, index)
            resolved_request = _resolve_references(operation_request, client_nodes, declared_client_ids)
            result = executor.execute(resolved_request)
            if not isinstance(result, dict):
                raise BlendexError("EXECUTION_FAILED", "Executor result must be an object.")
            _record_created_node(operation_request, result, client_nodes)
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
        except BlendexError as error:
            results.append(_operation_error_result(index, operation, error))
        except Exception as error:
            blendex_error = BlendexError("EXECUTION_FAILED", str(error) or error.__class__.__name__)
            results.append(_operation_error_result(index, operation, blendex_error))

    status = _status_for(results)
    error = _first_error(results)
    record = BatchRecord(
        batch_id=batch_id,
        status=status,
        operation_count=len(operations),
        target=copy.deepcopy(request.target),
        summary=request.params.get("summary", ""),
        operations=results,
        preview=_batch_preview(results),
        error=error,
    )
    STATE.record_batch(record)
    payload = record.to_dict()
    payload["confirmed"] = True
    return payload
