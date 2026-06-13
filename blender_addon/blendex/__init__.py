import pathlib
import sys


def _ensure_source_tree_protocol_path():
    root = pathlib.Path(__file__).resolve().parents[2]
    src = root / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


_ensure_source_tree_protocol_path()


bl_info = {
    "name": "BlendeX",
    "author": "BlendeX Contributors",
    "version": (0, 21, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BlendeX",
    "description": "CodeX bridge for structured Geometry Nodes operations",
    "category": "Node",
}

try:
    import bpy

    _OperatorBase = bpy.types.Operator
except ImportError:
    _OperatorBase = object


class BLENDEX_OT_start_service(_OperatorBase):
    bl_idname = "blendex.start_service"
    bl_label = "Start BlendeX Service"

    def execute(self, context):
        from . import server

        server.start_service()
        return {"FINISHED"}


class BLENDEX_OT_stop_service(_OperatorBase):
    bl_idname = "blendex.stop_service"
    bl_label = "Stop BlendeX Service"

    def execute(self, context):
        from . import server

        server.stop_service()
        return {"FINISHED"}


class BLENDEX_OT_undo_last_batch(_OperatorBase):
    bl_idname = "blendex.undo_last_batch"
    bl_label = "Undo Last BlendeX Batch"

    def execute(self, context):
        from .batches import undo_last_batch

        undo_last_batch()
        return {"FINISHED"}


def _load_classes():
    from .ui import panel_classes

    return [BLENDEX_OT_start_service, BLENDEX_OT_stop_service, BLENDEX_OT_undo_last_batch] + panel_classes()


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
