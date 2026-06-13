import importlib
import sys
import types
import unittest
from unittest.mock import patch


class BlendexUiTests(unittest.TestCase):
    def test_panel_subclasses_blender_panel_when_bpy_is_available(self):
        class FakePanel:
            pass

        fake_bpy = types.SimpleNamespace(types=types.SimpleNamespace(Panel=FakePanel))

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

        class_ids = {cls.bl_idname for cls in addon._load_classes() if hasattr(cls, "bl_idname")}
        self.assertIn("blendex.undo_last_batch", class_ids)
        self.assertTrue(issubclass(addon.BLENDEX_OT_undo_last_batch, FakeOperator))
        sys.modules.pop("blender_addon.blendex", None)
        sys.modules.pop("blender_addon.blendex.ui", None)


if __name__ == "__main__":
    unittest.main()
