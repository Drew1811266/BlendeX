bl_info = {
    "name": "BlendeX",
    "author": "BlendeX Contributors",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BlendeX",
    "description": "CodeX bridge for structured Geometry Nodes operations",
    "category": "Node",
}


def _load_classes():
    from .ui import panel_classes

    return panel_classes()


def register():
    import bpy

    for cls in _load_classes():
        bpy.utils.register_class(cls)


def unregister():
    import bpy

    for cls in reversed(_load_classes()):
        bpy.utils.unregister_class(cls)
