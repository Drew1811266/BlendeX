from typing import Any, Dict

from blendex_protocol.validation import ALLOWED_OPERATIONS


def scan_capabilities(runtime: Any) -> Dict[str, Any]:
    version = list(getattr(runtime, "version", (0, 0, 0)))
    node_types = getattr(runtime, "node_types", {})
    return {
        "blender_version": version,
        "node_types": node_types,
        "supported_operations": sorted(ALLOWED_OPERATIONS),
    }


def scan_bpy_capabilities() -> Dict[str, Any]:
    import bpy

    node_types: Dict[str, Dict[str, Any]] = {}
    for subclass in bpy.types.GeometryNode.__subclasses__():
        identifier = getattr(subclass, "__name__", "")
        if identifier.startswith("GeometryNode"):
            node_types[identifier] = {"inputs": [], "outputs": []}
    runtime = type("BpyRuntime", (), {"version": bpy.app.version, "node_types": node_types})()
    return scan_capabilities(runtime)
