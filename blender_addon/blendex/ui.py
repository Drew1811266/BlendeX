from .state import STATE

try:
    import bpy

    _PanelBase = bpy.types.Panel
except ImportError:
    _PanelBase = object


class BLENDEX_PT_panel(_PanelBase):
    bl_label = "BlendeX"
    bl_idname = "BLENDEX_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BlendeX"

    def draw(self, context):
        layout = self.layout
        status = "Running" if STATE.service_running else "Stopped"
        connected = "Connected" if STATE.client_connected else "No CodeX client"
        authenticated = "Authenticated" if STATE.client_authenticated else "Not authenticated"
        layout.label(text=f"Service: {status}")
        layout.label(text=f"Client: {connected}")
        layout.label(text=f"Auth: {authenticated}")
        if STATE.last_auth_error:
            layout.label(text=f"Auth Error: {STATE.last_auth_error}", icon="ERROR")
        layout.label(text=f"Port: {STATE.port}")
        layout.label(text=f"Token: {STATE.session_token[:6]}...")
        layout.operator("blendex.start_service", text="Start Service")
        layout.operator("blendex.stop_service", text="Stop Service")
        layout.separator()
        layout.label(text="Recent Operations")
        for log in STATE.recent_logs[:8]:
            icon = "CHECKMARK" if log.ok else "ERROR"
            layout.label(text=f"{log.operation}: {log.message}", icon=icon)


def panel_classes():
    return [BLENDEX_PT_panel]
