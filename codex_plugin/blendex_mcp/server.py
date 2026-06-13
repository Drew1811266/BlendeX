import json
import math
import sys
import uuid
from typing import Any, Dict, Optional

from .blender_client import BlenderClient
from .recipes import REGISTRY
from .tools import TOOL_DEFINITIONS, tool_to_operation
from .version import VERSION

MAX_JSON_VALUE_DEPTH = 100


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
        if _is_json_value_schema(schema):
            return _json_value_matches(value)
        return any(_value_matches_schema(value, option) for option in schema["oneOf"])
    schema_type = schema.get("type")
    if schema_type == "string":
        if not isinstance(value, str):
            return False
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            return False
        return True
    if schema_type == "number":
        return _number_matches(value)
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
        additional_properties = schema.get("additionalProperties", True)
        if extra_keys and additional_properties is False:
            return False
        for key in schema.get("required", []):
            if key not in value:
                return False
            if (
                key in {"id", "type"}
                and schema.get("properties", {}).get(key, {}).get("type") == "string"
                and (not isinstance(value[key], str) or not value[key].strip())
            ):
                return False
        for key, prop_value in value.items():
            if not isinstance(key, str):
                return False
            prop_schema = properties.get(key)
            if prop_schema is not None:
                if not _value_matches_schema(prop_value, prop_schema):
                    return False
            elif not _json_value_matches(prop_value):
                return False
        return True
    return True


def _is_json_value_schema(schema: Dict[str, Any]) -> bool:
    options = schema.get("oneOf")
    if not isinstance(options, list):
        return False
    return {option.get("type") for option in options} == {
        "array",
        "boolean",
        "null",
        "number",
        "object",
        "string",
    }


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


def _number_matches(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value.bit_length() <= 53
    if isinstance(value, float):
        return math.isfinite(value)
    return False


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


def _recipe_error_code(error: ValueError) -> str:
    if str(error).startswith("Unknown recipe:"):
        return "RECIPE_NOT_FOUND"
    return "VALIDATION_FAILED"


def _handle_local_recipe_operation(operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    operation_type = operation.get("type")
    if operation_type == "recipes.list":
        return _tool_result({"ok": True, "result": {"recipes": REGISTRY.list_recipes()}})
    if operation_type == "recipes.build_batch":
        try:
            operations = REGISTRY.build(
                operation["params"]["recipe_id"],
                operation["params"].get("parameters", {}),
            )
        except ValueError as error:
            return _tool_result(
                {
                    "ok": False,
                    "error": {"code": _recipe_error_code(error), "message": str(error)},
                }
            )
        return _tool_result({"ok": True, "result": {"operations": operations}})
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
                "serverInfo": {"name": "blendex", "version": VERSION},
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
        local_result = _handle_local_recipe_operation(operation)
        if local_result is not None:
            return json_rpc_success(message_id, local_result)
        try:
            result = client.send_operation(operation)
        except (ConnectionError, OSError, TimeoutError, json.JSONDecodeError) as error:
            return json_rpc_error(message_id, -32000, f"BlendeX client error: {error}")
        return json_rpc_success(message_id, _tool_result(result))
    return json_rpc_error(message_id, -32601, f"Method not found: {method}")


def handle_line(line: str, client: BlenderClient) -> Optional[str]:
    try:
        message = json.loads(line)
    except (json.JSONDecodeError, RecursionError, ValueError):
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
