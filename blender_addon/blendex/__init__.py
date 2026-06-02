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
    import bpy
    from . import server
    from .ui import panel_classes

    class BLENDEX_OT_start_service(bpy.types.Operator):
        bl_idname = "blendex.start_service"
        bl_label = "Start BlendeX Service"

        def execute(self, context):
            server.start_service()
            return {"FINISHED"}

    class BLENDEX_OT_stop_service(bpy.types.Operator):
        bl_idname = "blendex.stop_service"
        bl_label = "Stop BlendeX Service"

        def execute(self, context):
            server.stop_service()
            return {"FINISHED"}

    return [BLENDEX_OT_start_service, BLENDEX_OT_stop_service] + panel_classes()


def register():
    import bpy

    for cls in _load_classes():
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    from . import server

    server.stop_service()
    for cls in reversed(_load_classes()):
        bpy.utils.unregister_class(cls)
