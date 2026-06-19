import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_blender_addon import build_package


class PackagingTests(unittest.TestCase):
    def test_blender_addon_package_contains_addon_and_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path = build_package(Path(tmp))

            self.assertTrue(package_path.exists())
            self.assertEqual(package_path.name, "blendex-0.39.0-blender-addon.zip")
            with zipfile.ZipFile(package_path) as archive:
                names = set(archive.namelist())

        self.assertIn("blendex/__init__.py", names)
        self.assertIn("blendex/server.py", names)
        self.assertIn("blendex_protocol/messages.py", names)
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith(".pyc") for name in names))


if __name__ == "__main__":
    unittest.main()
