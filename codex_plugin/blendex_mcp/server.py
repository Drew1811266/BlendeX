import json
import sys
import uuid
from typing import Any, Dict

from .blender_client import BlenderClient
from .tools import TOOL_DEFINITIONS, tool_to_operation


def _content(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def handle_message(message: Dict[str, Any], client: BlenderClient) -> Dict[str, Any]:
    method = message.get("method")
    message_id = message.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "blendex", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": TOOL_DEFINITIONS}}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        operation = tool_to_operation(name, arguments, request_id=f"req_{uuid.uuid4().hex[:12]}")
        result = client.send_operation(operation)
        return {"jsonrpc": "2.0", "id": message_id, "result": _content(result)}
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main() -> None:
    client = BlenderClient()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_message(json.loads(line), client)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
