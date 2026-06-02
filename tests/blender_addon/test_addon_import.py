import os
import pathlib
import subprocess
import sys
import unittest


class AddonImportTests(unittest.TestCase):
    def test_source_tree_addon_bootstraps_protocol_package(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root / "blender_addon")

        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import blendex; from blendex import server; print(server.__name__)",
            ],
            cwd=str(root),
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("blendex.server", completed.stdout)


if __name__ == "__main__":
    unittest.main()
