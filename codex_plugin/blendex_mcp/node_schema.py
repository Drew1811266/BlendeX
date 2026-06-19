import copy
import math
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "node_capability.v2"
_MISSING = object()


def _read_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if not isinstance(value, (str, bytes)):
        try:
            return [_json_safe(item) for item in value]
        except TypeError:
            pass
    return str(value)


def _normalize_enum_item(item: Any) -> Dict[str, str]:
    if isinstance(item, str):
        return {"identifier": item, "name": item}
    identifier = _read_value(item, "identifier", "")
    name = _read_value(item, "name", identifier)
    if not identifier:
        identifier = name
    if not name:
        name = identifier
    return {"identifier": str(identifier), "name": str(name)}


def _normalize_enum_items(raw_items: Any) -> List[Dict[str, str]]:
    if raw_items in (None, _MISSING):
        return []
    try:
        items = list(raw_items)
    except TypeError:
        return []
    return [_normalize_enum_item(item) for item in items]


def normalize_socket(socket: Any, *, direction: str) -> Dict[str, Any]:
    if isinstance(socket, str):
        name = socket
        identifier = socket
        socket_type = ""
        default_value = None
        enum_items: Iterable[Any] = []
        is_multi_input = False
        is_field = False
    else:
        name = _read_value(socket, "name", "")
        identifier = _read_value(socket, "identifier", name)
        socket_type = _read_value(
            socket,
            "socket_type",
            _read_value(socket, "bl_socket_idname", ""),
        )
        default_value = _read_value(socket, "default_value", None)
        enum_items = _read_value(socket, "enum_items", [])
        is_multi_input = bool(_read_value(socket, "is_multi_input", False))
        is_field = bool(
            _read_value(
                socket,
                "is_field",
                _read_value(socket, "supports_field", False),
            )
        )
    if not identifier:
        identifier = name
    if not name:
        name = identifier
    return {
        "name": str(name),
        "identifier": str(identifier),
        "socket_type": str(socket_type or ""),
        "direction": direction,
        "is_multi_input": is_multi_input,
        "is_field": is_field,
        "default_value": _json_safe(default_value),
        "enum_items": _normalize_enum_items(enum_items),
    }


def normalize_sockets(sockets: Any, *, direction: str) -> List[Dict[str, Any]]:
    if sockets is None:
        return []
    return [normalize_socket(socket, direction=direction) for socket in sockets]


def normalize_node_capability(identifier: str, capability: Any = None) -> Dict[str, Any]:
    source = copy.deepcopy(capability) if isinstance(capability, dict) else {}
    display_name = source.get("display_name") or _read_value(capability, "display_name", identifier)
    inputs = normalize_sockets(source.get("inputs", _read_value(capability, "inputs", [])), direction="input")
    outputs = normalize_sockets(source.get("outputs", _read_value(capability, "outputs", [])), direction="output")
    metadata_complete = source.get("metadata_complete")
    if metadata_complete is None:
        metadata_complete = bool(inputs or outputs)

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "display_name": str(display_name or identifier),
        "inputs": inputs,
        "outputs": outputs,
        "metadata_complete": bool(metadata_complete),
    }
    for key, value in source.items():
        if key not in normalized and key not in {"inputs", "outputs"}:
            normalized[key] = value
    return normalized
