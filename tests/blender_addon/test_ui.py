import importlib
import sys
import types
import unittest
from unittest.mock import patch

from blender_addon.blendex.history import BatchRecord


class FakeLayout:
    def __init__(self):
        self.labels = []
        self.operators = []
        self.separators = 0

    def label(self, text="", icon=None):
        self.labels.append({"text": text, "icon": icon})

    def operator(self, operator_id, text=""):
        self.operators.append({"operator_id": operator_id, "text": text})

    def separator(self):
        self.separators += 1


class BlendexUiTests(unittest.TestCase):
    def _restore_addon_module(self, addon):
        package = sys.modules.get("blender_addon")
        if package is not None:
            setattr(package, "blendex", addon)
        sys.modules["blender_addon.blendex"] = addon

    def tearDown(self):
        package = sys.modules.get("blender_addon")
        addon = getattr(package, "blendex", None)
        if addon is not None and "blender_addon.blendex" not in sys.modules:
            sys.modules["blender_addon.blendex"] = addon
        from blender_addon.blendex.state import STATE

        STATE.service_running = False
        STATE.client_connected = False
        STATE.client_authenticated = False
        STATE.last_auth_error = ""
        STATE.recent_logs.clear()
        STATE.batch_history.records.clear()

    def test_panel_subclasses_blender_panel_when_bpy_is_available(self):
        class FakeOperator:
            pass

        class FakePanel:
            pass

        fake_bpy = types.SimpleNamespace(types=types.SimpleNamespace(Operator=FakeOperator, Panel=FakePanel))

        with patch.dict(sys.modules, {"bpy": fake_bpy}):
            sys.modules.pop("blender_addon.blendex.ui", None)
            ui = importlib.import_module("blender_addon.blendex.ui")

        self.assertTrue(issubclass(ui.BLENDEX_PT_panel, FakePanel))
        sys.modules.pop("blender_addon.blendex.ui", None)

    def test_undo_operator_is_registered_with_addon_classes(self):
        class FakeOperator:
            pass

        class FakePanel:
            pass

        fake_bpy = types.SimpleNamespace(
            types=types.SimpleNamespace(Operator=FakeOperator, Panel=FakePanel),
        )

        with patch.dict(sys.modules, {"bpy": fake_bpy}):
            sys.modules.pop("blender_addon.blendex", None)
            sys.modules.pop("blender_addon.blendex.ui", None)
            addon = importlib.import_module("blender_addon.blendex")
        self._restore_addon_module(addon)

        class_ids = {cls.bl_idname for cls in addon._load_classes() if hasattr(cls, "bl_idname")}
        self.assertIn("blendex.undo_last_batch", class_ids)
        self.assertTrue(issubclass(addon.BLENDEX_OT_undo_last_batch, FakeOperator))

    def test_undo_operator_reports_blendex_error_and_cancels(self):
        class FakeOperator:
            def __init__(self):
                self.reports = []

            def report(self, levels, message):
                self.reports.append((levels, message))

        class FakePanel:
            pass

        fake_bpy = types.SimpleNamespace(
            types=types.SimpleNamespace(Operator=FakeOperator, Panel=FakePanel),
        )

        with patch.dict(sys.modules, {"bpy": fake_bpy}):
            sys.modules.pop("blender_addon.blendex", None)
            sys.modules.pop("blender_addon.blendex.ui", None)
            addon = importlib.import_module("blender_addon.blendex")
        self._restore_addon_module(addon)

        from blender_addon.blendex.state import STATE

        STATE.batch_history.records.clear()
        operator = addon.BLENDEX_OT_undo_last_batch()

        result = operator.execute(context=None)

        self.assertEqual(result, {"CANCELLED"})
        self.assertEqual(
            operator.reports,
            [({"ERROR"}, "UNDO_UNAVAILABLE: No BlendeX batch is available to undo.")],
        )

    def test_panel_draws_latest_batch_summary_and_undo_status(self):
        from blender_addon.blendex.state import STATE
        from blender_addon.blendex.ui import BLENDEX_PT_panel

        STATE.service_running = True
        STATE.client_connected = True
        STATE.client_authenticated = True
        STATE.batch_history.records.clear()
        STATE.record_batch(
            BatchRecord(
                batch_id="batch_ui",
                status="succeeded",
                operation_count=3,
                target={"object_id": "Cube"},
                summary="Create linked test graph",
                operations=[],
                preview={},
                execution_summary={
                    "succeeded_operations": 3,
                    "failed_operations": 0,
                    "undo_available": True,
                },
            )
        )
        panel = BLENDEX_PT_panel()
        panel.layout = FakeLayout()

        panel.draw(context=None)

        labels = [entry["text"] for entry in panel.layout.labels]
        self.assertIn("Service: Running", labels)
        self.assertIn("Client: Connected", labels)
        self.assertTrue(any("Create linked test graph" in label for label in labels))
        self.assertTrue(any("3 ops" in label for label in labels))
        self.assertTrue(any("undo available" in label for label in labels))
        self.assertIn({"operator_id": "blendex.undo_last_batch", "text": "Undo Last Batch"}, panel.layout.operators)


if __name__ == "__main__":
    unittest.main()
