from typing import Any, Dict, List


TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "blendex_scan_capabilities",
        "description": "Scan the connected Blender runtime for supported Geometry Nodes capabilities.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "blendex_inspect_scene",
        "description": "Inspect the current Blender scene and selected object.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "blendex_create_node",
        "description": "Create a Geometry Nodes node on a target object and modifier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": {"type": "string"},
                "modifier_id": {"type": "string"},
                "node_type": {"type": "string"},
                "label": {"type": "string"},
            },
            "required": ["object_id", "node_type"],
            "additionalProperties": False,
        },
    },
]


def tool_names() -> List[str]:
    return [tool["name"] for tool in TOOL_DEFINITIONS]


def tool_to_operation(name: str, arguments: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    if name == "blendex_scan_capabilities":
        return {"id": request_id, "type": "capabilities.scan", "target": {}, "params": {}}
    if name == "blendex_inspect_scene":
        return {"id": request_id, "type": "scene.inspect", "target": {}, "params": {}}
    if name == "blendex_create_node":
        return {
            "id": request_id,
            "type": "geometry_nodes.create_node",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {
                "node_type": arguments["node_type"],
                "label": arguments.get("label", arguments["node_type"]),
            },
        }
    raise ValueError(f"Unknown BlendeX tool: {name}")
