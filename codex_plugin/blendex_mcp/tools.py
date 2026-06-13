from typing import Any, Dict, List


STRING_PROP = {"type": "string"}
NON_EMPTY_STRING_PROP = {"type": "string", "minLength": 1}
NUMBER_PROP = {"type": "number"}
JSON_VALUE_PROP = {
    "oneOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {"type": "array"},
        {"type": "object"},
        {"type": "null"},
    ]
}
OPERATION_ARRAY_PROP = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "properties": {
            "id": STRING_PROP,
            "type": STRING_PROP,
            "target": {"type": "object"},
            "params": {"type": "object"},
        },
        "required": ["id", "type"],
        "additionalProperties": True,
    },
}


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
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "node_type": STRING_PROP,
                "label": STRING_PROP,
                "location": {"type": "array", "items": NUMBER_PROP, "minItems": 2, "maxItems": 2},
                "client_id": STRING_PROP,
            },
            "required": ["object_id", "node_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_create_carrier_mesh",
        "description": "Create a carrier mesh object for BlendeX Geometry Nodes workflows.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": STRING_PROP},
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_create_modifier",
        "description": "Create a Geometry Nodes modifier on an object.",
        "inputSchema": {
            "type": "object",
            "properties": {"object_id": STRING_PROP, "modifier_id": STRING_PROP},
            "required": ["object_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_inspect_tree",
        "description": "Inspect a Geometry Nodes modifier tree.",
        "inputSchema": {
            "type": "object",
            "properties": {"object_id": STRING_PROP, "modifier_id": STRING_PROP},
            "required": ["object_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_set_socket_value",
        "description": "Set a Geometry Nodes socket value.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "node_id": STRING_PROP,
                "socket": STRING_PROP,
                "value": JSON_VALUE_PROP,
            },
            "required": ["object_id", "node_id", "socket", "value"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_link_sockets",
        "description": "Create a link between two Geometry Nodes sockets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "from_node": STRING_PROP,
                "from_socket": STRING_PROP,
                "to_node": STRING_PROP,
                "to_socket": STRING_PROP,
            },
            "required": ["object_id", "from_node", "from_socket", "to_node", "to_socket"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_label_node",
        "description": "Set a display label on a Geometry Nodes node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_id": STRING_PROP,
                "modifier_id": STRING_PROP,
                "node_id": STRING_PROP,
                "label": STRING_PROP,
            },
            "required": ["object_id", "node_id", "label"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_validate_batch",
        "description": "Validate a batch of BlendeX operations without executing them.",
        "inputSchema": {
            "type": "object",
            "properties": {"operations": OPERATION_ARRAY_PROP},
            "required": ["operations"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_dry_run",
        "description": "Dry-run a batch of BlendeX operations.",
        "inputSchema": {
            "type": "object",
            "properties": {"operations": OPERATION_ARRAY_PROP},
            "required": ["operations"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blendex_execute_confirmed_batch",
        "description": "Execute a previously dry-run BlendeX batch after user confirmation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": OPERATION_ARRAY_PROP,
                "confirmation_id": NON_EMPTY_STRING_PROP,
                "summary": NON_EMPTY_STRING_PROP,
                "preview": {"type": "object"},
            },
            "required": ["operations", "confirmation_id", "summary"],
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
                **({"location": arguments["location"]} if "location" in arguments else {}),
                **({"client_id": arguments["client_id"]} if "client_id" in arguments else {}),
            },
        }
    if name == "blendex_create_carrier_mesh":
        return {
            "id": request_id,
            "type": "scene.create_carrier_mesh",
            "target": {},
            "params": {"name": arguments.get("name", "BlendeX Carrier")},
        }
    if name == "blendex_create_modifier":
        return {
            "id": request_id,
            "type": "geometry_nodes.create_modifier",
            "target": {"object_id": arguments["object_id"]},
            "params": {"modifier_id": arguments.get("modifier_id", "BlendeX Geometry")},
        }
    if name == "blendex_inspect_tree":
        return {
            "id": request_id,
            "type": "geometry_nodes.inspect_tree",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {},
        }
    if name == "blendex_set_socket_value":
        return {
            "id": request_id,
            "type": "geometry_nodes.set_socket_value",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {
                "node_id": arguments["node_id"],
                "socket": arguments["socket"],
                "value": arguments["value"],
            },
        }
    if name == "blendex_link_sockets":
        return {
            "id": request_id,
            "type": "geometry_nodes.link_sockets",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {
                "from_node": arguments["from_node"],
                "from_socket": arguments["from_socket"],
                "to_node": arguments["to_node"],
                "to_socket": arguments["to_socket"],
            },
        }
    if name == "blendex_label_node":
        return {
            "id": request_id,
            "type": "geometry_nodes.label_node",
            "target": {
                "object_id": arguments["object_id"],
                "modifier_id": arguments.get("modifier_id", "BlendeX Geometry"),
            },
            "params": {"node_id": arguments["node_id"], "label": arguments["label"]},
        }
    if name == "blendex_validate_batch":
        return {
            "id": request_id,
            "type": "safety.validate_batch",
            "target": {},
            "params": {"operations": arguments["operations"]},
        }
    if name == "blendex_dry_run":
        return {
            "id": request_id,
            "type": "safety.dry_run",
            "target": {},
            "params": {"operations": arguments["operations"]},
        }
    if name == "blendex_execute_confirmed_batch":
        return {
            "id": request_id,
            "type": "safety.execute_batch",
            "target": {},
            "params": {
                "operations": arguments["operations"],
                "confirmed": True,
                "confirmation_id": arguments["confirmation_id"],
                "summary": arguments["summary"],
                "preview": arguments.get("preview", {}),
            },
        }
    raise ValueError(f"Unknown BlendeX tool: {name}")
