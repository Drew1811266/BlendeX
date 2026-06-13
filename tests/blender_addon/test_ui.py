import importlib
import sys
import types
import unittest
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
