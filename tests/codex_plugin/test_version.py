import json
import pathlib
import re
import unittest

from codex_plugin.blendex_mcp.version import VERSION


ROOT = pathlib.Path(__file__).resolve().parents[2]


class VersionTests(unittest.TestCase):
    def test_plugin_manifest_uses_runtime_version(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["version"], VERSION)

    def test_pyproject_uses_runtime_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text()

        self.assertIn(f'version = "{VERSION}"', pyproject)

    def test_blender_addon_uses_runtime_version_tuple(self):
        init_text = (ROOT / "blender_addon" / "blendex" / "__init__.py").read_text()
        expected_tuple = tuple(int(part) for part in VERSION.split("."))

        self.assertIn(f'"version": {expected_tuple}', init_text)

    def test_mcp_server_reports_runtime_version(self):
        server_text = (ROOT / "codex_plugin" / "blendex_mcp" / "server.py").read_text()

        self.assertIn('"version": VERSION', server_text)

    def test_readme_names_development_track(self):
        readme = (ROOT / "README.md").read_text()

        self.assertRegex(readme, re.compile(r"v0\.3", re.IGNORECASE))
