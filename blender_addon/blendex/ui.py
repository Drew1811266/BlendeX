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

    def _batch_icon(self, batch):
        if batch.status == "succeeded":
            return "CHECKMARK"
        if batch.status == "partial":
            return "INFO"
        return "ERROR"

    def _batch_undo_text(self, batch):
        if batch.undo_status == "undone":
            return "undo done"
        if batch.undo_status in {"unavailable", "failed"}:
            return f"undo {batch.undo_status}"
        execution_summary = batch.execution_summary if isinstance(batch.execution_summary, dict) else {}
        return "undo available" if execution_summary.get("undo_available") else "undo unavailable"

    def _batch_text(self, batch):
        summary = batch.summary or batch.batch_id
        return f"{batch.status}: {summary} ({batch.operation_count} ops, {self._batch_undo_text(batch)})"

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
        layout.operator("blendex.undo_last_batch", text="Undo Last Batch")
        layout.separator()
        layout.label(text="Recent Operations")
        for log in STATE.recent_logs[:8]:
            icon = "CHECKMARK" if log.ok else "ERROR"
            layout.label(text=f"{log.operation}: {log.message}", icon=icon)
        layout.separator()
        layout.label(text="Recent Batches")
        batches = STATE.recent_batches(5)
        if not batches:
            layout.label(text="No recent batches")
        for batch in batches:
            layout.label(text=self._batch_text(batch), icon=self._batch_icon(batch))


def panel_classes():
    return [BLENDEX_PT_panel]
