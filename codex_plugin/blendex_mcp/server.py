import json
import sys
import uuid
from typing import Any, Dict, Optional

from .blender_client import BlenderClient
from .tools import TOOL_DEFINITIONS, tool_to_operation


def _content(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def json_rpc_success(message_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def json_rpc_error(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _message_id(message: Any) -> Optional[Any]:
    if isinstance(message, dict):
        return message.get("id")
    return None


def _invalid_params(message_id: Any, message: str) -> Dict[str, Any]:
    return json_rpc_error(message_id, -32602, message)


def _validate_tool_call_params(params: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(params, dict):
        return None
    name = params.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return None
    return {"name": name, "arguments": arguments}


def _validate_tool_arguments(name: str, arguments: Dict[str, Any]) -> Optional[str]:
    if name in {"blendex_scan_capabilities", "blendex_inspect_scene"}:
        if arguments:
            return "Invalid params: tool does not accept arguments"
        return None
    if name == "blendex_create_node":
        allowed = {"object_id", "modifier_id", "node_type", "label"}
        extra_keys = sorted(set(arguments) - allowed)
        if extra_keys:
            return f"Invalid params: unexpected argument {extra_keys[0]}"
        required = {"object_id", "node_type"}
        missing_keys = sorted(required - set(arguments))
        if missing_keys:
            return f"Invalid params: missing argument {missing_keys[0]}"
        for key in ("object_id", "node_type", "modifier_id", "label"):
            if key in arguments and not isinstance(arguments[key], str):
                return f"Invalid params: {key} must be a string"
    return None


def handle_message(message: Dict[str, Any], client: BlenderClient) -> Optional[Dict[str, Any]]:
    message_id = _message_id(message)
    if not isinstance(message, dict):
        return json_rpc_error(message_id, -32600, "Invalid Request")
    if "id" not in message:
        return None
    if message.get("jsonrpc") != "2.0":
        return json_rpc_error(message_id, -32600, "Invalid Request")
    method = message.get("method")
    if not isinstance(method, str) or not method:
        return json_rpc_error(message_id, -32600, "Invalid Request")
    if method == "initialize":
        return json_rpc_success(
            message_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "blendex", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return json_rpc_success(message_id, {"tools": TOOL_DEFINITIONS})
    if method == "tools/call":
        params = _validate_tool_call_params(message.get("params", {}))
        if params is None:
            return _invalid_params(message_id, "Invalid params")
        argument_error = _validate_tool_arguments(params["name"], params["arguments"])
        if argument_error is not None:
            return _invalid_params(message_id, argument_error)
        try:
            operation = tool_to_operation(
                params["name"],
                params["arguments"],
                request_id=f"req_{uuid.uuid4().hex[:12]}",
            )
        except ValueError as error:
            return json_rpc_error(message_id, -32601, str(error))
        except (KeyError, TypeError) as error:
            return _invalid_params(message_id, f"Invalid params: {error}")
        try:
            result = client.send_operation(operation)
        except (ConnectionError, OSError, TimeoutError, json.JSONDecodeError) as error:
            return json_rpc_error(message_id, -32000, f"BlendeX client error: {error}")
        return json_rpc_success(message_id, _content(result))
    return json_rpc_error(message_id, -32601, f"Method not found: {method}")


def handle_line(line: str, client: BlenderClient) -> Optional[str]:
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        response = json_rpc_error(None, -32700, "Parse error")
    else:
        response = handle_message(message, client)
    if response is None:
        return None
    return json.dumps(response)


def main() -> None:
    client = BlenderClient()
    for line in sys.stdin:
        if not line.strip():
            continue
        response_line = handle_line(line, client)
        if response_line is not None:
            sys.stdout.write(response_line + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
