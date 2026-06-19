#!/usr/bin/env python3
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from codex_plugin.blendex_mcp.blender_client import BlenderClient
from codex_plugin.blendex_mcp.server import handle_line
from codex_plugin.blendex_mcp.version import VERSION


INITIALIZE_REQUEST = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
TOOLS_LIST_REQUEST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}


def _response(line):
    if line is None:
        raise RuntimeError("MCP server returned no response.")
    payload = json.loads(line)
    if "error" in payload:
        raise RuntimeError(payload["error"]["message"])
    return payload["result"]


def main() -> int:
    client = BlenderClient()
    initialize = _response(handle_line(json.dumps(INITIALIZE_REQUEST), client))
    server_info = initialize["serverInfo"]
    if server_info["version"] != VERSION:
        raise RuntimeError(f"MCP version mismatch: {server_info['version']} != {VERSION}")

    tools = _response(handle_line(json.dumps(TOOLS_LIST_REQUEST), client))["tools"]
    if len(tools) < 18:
        raise RuntimeError(f"Expected at least 18 BlendeX tools, got {len(tools)}")

    print(f"MCP probe OK: {server_info['name']} {VERSION}, {len(tools)} tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
