import json
import sys
import uuid
from typing import Any, Dict, Optional

from .blender_client import BlenderClient
from .tools import TOOL_DEFINITIONS, tool_to_operation


def _content(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _tool_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = _content(payload)
    if payload.get("ok") is False:
        result["isError"] = True
    return result


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


def _tool_schema(name: str) -> Optional[Dict[str, Any]]:
    for tool in TOOL_DEFINITIONS:
        if tool["name"] == name:
            return tool["inputSchema"]
    return None


def _value_matches_schema(value: Any, schema: Dict[str, Any]) -> bool:
    if "oneOf" in schema:
        return any(_value_matches_schema(value, option) for option in schema["oneOf"])
    schema_type = schema.get("type")
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "null":
        return value is None
    if schema_type == "array":
        if not isinstance(value, list):
            return False
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            return False
        max_items = schema.get("maxItems")
        if max_items is not None and len(value) > max_items:
            return False
        item_schema = schema.get("items")
        if item_schema is None:
            return True
        return all(_value_matches_schema(item, item_schema) for item in value)
    if schema_type == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        extra_keys = set(value) - set(properties)
        if extra_keys and schema.get("additionalProperties") is False:
            return False
        for key in schema.get("required", []):
            if key not in value:
                return False
        return all(
            prop_schema is None or _value_matches_schema(prop_value, prop_schema)
            for key, prop_value in value.items()
            for prop_schema in [properties.get(key)]
        )
    return True


def _validate_tool_arguments(name: str, arguments: Dict[str, Any]) -> Optional[str]:
    schema = _tool_schema(name)
    if schema is None:
        return None
    properties = schema.get("properties", {})
    extra_keys = sorted(set(arguments) - set(properties))
    if extra_keys and schema.get("additionalProperties") is False:
        return f"Invalid params: unexpected argument {extra_keys[0]}"
    for key in schema.get("required", []):
        if key not in arguments:
            return f"Invalid params: missing argument {key}"
    for key, value in arguments.items():
        prop_schema = properties.get(key)
        if prop_schema is not None and not _value_matches_schema(value, prop_schema):
            return f"Invalid params: {key} has invalid type"
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
        return json_rpc_success(message_id, _tool_result(result))
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
