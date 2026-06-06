import copy
from typing import Any, Dict, Iterable

try:
    from codex_plugin.blendex_mcp.catalog import semantic_for_node
except Exception:

    def semantic_for_node(node_type: str) -> Dict[str, Any]:
        return {}


IMPLEMENTED_OPERATIONS = {
    "capabilities.scan",
    "capabilities.supported_operations",
    "scene.inspect",
    "geometry_nodes.inspect_tree",
    "geometry_nodes.create_node",
}


def _socket_template_to_dict(template: Any) -> Dict[str, Any]:
    return {
        "name": getattr(template, "name", ""),
        "identifier": getattr(template, "identifier", getattr(template, "name", "")),
        "socket_type": getattr(template, "bl_socket_idname", template.__class__.__name__),
    }


def _read_templates(node_class: Any, method_name: str) -> list:
    method = getattr(node_class, method_name, None)
    if not callable(method):
        return []
    sockets = []
    index = 0
    while index < 64:
        try:
            template = method(index)
        except Exception:
            break
        if template is None:
            break
        sockets.append(_socket_template_to_dict(template))
        index += 1
    return sockets


def _semantic_for_identifier(identifier: str) -> Dict[str, Any]:
    return copy.deepcopy(semantic_for_node(identifier))


def _node_capability(identifier: str, node_class: Any = None) -> Dict[str, Any]:
    inputs = _read_templates(node_class, "input_template") if node_class is not None else []
    outputs = _read_templates(node_class, "output_template") if node_class is not None else []
    metadata_complete = bool(inputs or outputs)
    capability = {
        "display_name": identifier,
        "inputs": inputs,
        "outputs": outputs,
        "metadata_complete": metadata_complete,
    }
    semantic = _semantic_for_identifier(identifier)
    if semantic:
        capability["semantic"] = semantic
    return capability


def _safe_subclasses(base_class: Any) -> Iterable[Any]:
    if base_class is None:
        return []
    subclasses = getattr(base_class, "__subclasses__", None)
    if not callable(subclasses):
        return []
    try:
        return subclasses()
    except Exception:
        return []


def _add_node_class(
    node_types: Dict[str, Dict[str, Any]],
    node_class: Any,
    expected_prefixes: tuple[str, ...] = (),
) -> None:
    if node_class is None:
        return
    identifier = getattr(node_class, "__name__", "")
    if not identifier:
        return
    if expected_prefixes and not identifier.startswith(expected_prefixes):
        return
    if identifier in node_types:
        return
    node_types[identifier] = _node_capability(identifier, node_class)


def scan_capabilities(runtime: Any) -> Dict[str, Any]:
    version = list(getattr(runtime, "version", (0, 0, 0)))
    runtime_node_types = getattr(runtime, "node_types", {})
    node_types: Dict[str, Dict[str, Any]] = {}
    for identifier, capability in runtime_node_types.items():
        node_capability = copy.deepcopy(capability)
        node_capability.setdefault("inputs", [])
        node_capability.setdefault("outputs", [])
        node_capability.setdefault(
            "metadata_complete",
            bool(node_capability["inputs"] or node_capability["outputs"]),
        )
        semantic = _semantic_for_identifier(identifier)
        if semantic:
            node_capability["semantic"] = semantic
        node_types[identifier] = node_capability
    return {
        "blender_version": version,
        "node_types": node_types,
        "supported_operations": sorted(IMPLEMENTED_OPERATIONS),
    }


def scan_bpy_capabilities() -> Dict[str, Any]:
    import bpy

    node_types: Dict[str, Dict[str, Any]] = {}
    bpy_types = getattr(bpy, "types", None)
    if bpy_types is not None:
        for subclass in _safe_subclasses(getattr(bpy_types, "GeometryNode", None)):
            _add_node_class(node_types, subclass, ("GeometryNode",))
        for subclass in _safe_subclasses(getattr(bpy_types, "FunctionNode", None)):
            _add_node_class(node_types, subclass, ("FunctionNode",))
        for subclass in _safe_subclasses(getattr(bpy_types, "ShaderNode", None)):
            _add_node_class(node_types, subclass, ("ShaderNode",))
        _add_node_class(node_types, getattr(bpy_types, "NodeGroupInput", None))
        _add_node_class(node_types, getattr(bpy_types, "NodeGroupOutput", None))
    runtime = type("BpyRuntime", (), {"version": bpy.app.version, "node_types": node_types})()
    return scan_capabilities(runtime)
