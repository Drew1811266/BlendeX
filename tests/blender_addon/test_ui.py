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


if __name__ == "__main__":
    unittest.main()
