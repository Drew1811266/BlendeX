from typing import Any, Dict

try:
    from codex_plugin.blendex_mcp.catalog import semantic_for_node
except Exception:

    def semantic_for_node(node_type: str) -> Dict[str, Any]:
        return {}


IMPLEMENTED_OPERATIONS = {
    "capabilities.scan",
    "capabilities.supported_operations",
    "scene.inspect",
    "scene.create_carrier_mesh",
    "geometry_nodes.create_modifier",
    "geometry_nodes.inspect_tree",
    "geometry_nodes.create_node",
    "geometry_nodes.link_sockets",
    "geometry_nodes.set_socket_value",
    "geometry_nodes.label_node",
    "geometry_nodes.mark_ownership",
    "safety.validate_batch",
    "safety.dry_run",
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
    semantic = semantic_for_node(identifier)
    if semantic:
        capability["semantic"] = semantic
    return capability


def scan_capabilities(runtime: Any) -> Dict[str, Any]:
    version = list(getattr(runtime, "version", (0, 0, 0)))
    runtime_node_types = getattr(runtime, "node_types", {})
    node_types: Dict[str, Dict[str, Any]] = {}
    for identifier, capability in runtime_node_types.items():
        node_capability = dict(capability)
        node_capability.setdefault("inputs", [])
        node_capability.setdefault("outputs", [])
        node_capability.setdefault(
            "metadata_complete",
            bool(node_capability["inputs"] or node_capability["outputs"]),
        )
        semantic = semantic_for_node(identifier)
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
    for subclass in bpy.types.GeometryNode.__subclasses__():
        identifier = getattr(subclass, "__name__", "")
        if identifier.startswith("GeometryNode"):
            node_types[identifier] = _node_capability(identifier, subclass)
    runtime = type("BpyRuntime", (), {"version": bpy.app.version, "node_types": node_types})()
    return scan_capabilities(runtime)
