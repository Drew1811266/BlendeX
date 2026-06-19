import json
import pathlib
import re
import unittest

from codex_plugin.blendex_mcp.version import VERSION


ROOT = pathlib.Path(__file__).resolve().parents[2]


class VersionTests(unittest.TestCase):
    def test_v0_4_final_readiness_stage_is_0_40(self):
        self.assertEqual(VERSION, "0.40.0")

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

        self.assertRegex(readme, re.compile(r"v0\.4", re.IGNORECASE))
        self.assertIn("local beta", readme)

    def test_readme_does_not_list_completed_v0_3_trust_features_as_future_work(self):
        readme = (ROOT / "README.md").read_text()

        self.assertNotIn("用户确认机制。", readme)
        self.assertNotIn("本地连接鉴权。", readme)
        self.assertNotIn("undo last batch for supported reversible batches。", readme)

    def test_mcp_probe_script_exists(self):
        probe = ROOT / "scripts" / "mcp_probe.py"
        text = probe.read_text()

        self.assertIn('"method": "initialize"', text)
        self.assertIn('"method": "tools/list"', text)

    def test_release_check_script_runs_required_commands(self):
        script = ROOT / "scripts" / "run_release_checks.sh"
        text = script.read_text()

        self.assertIn("./scripts/run_unit_tests.sh", text)
        self.assertIn("python3 scripts/run_blender_smoke.py", text)
        self.assertIn("git diff --check", text)
        self.assertIn("python3 scripts/mcp_probe.py", text)
