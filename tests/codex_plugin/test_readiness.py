import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class ReadinessAuditTests(unittest.TestCase):
    def test_readiness_audit_declares_local_beta_ready_scope(self):
        audit = (ROOT / "docs" / "readiness-audit-v0.4.md").read_text()

        self.assertIn("BlendeX v0.4 Readiness Audit", audit)
        self.assertIn("Status: Ready for local beta", audit)
        self.assertIn("Blender 5.1.2", audit)
        self.assertIn("MCP probe OK", audit)
        for recipe_id in (
            "architecture.grid_tower",
            "architecture.wall_panel",
            "architecture.modular_building",
            "scatter.stones",
            "scatter.ground_points",
            "scatter.grass",
        ):
            self.assertIn(recipe_id, audit)


if __name__ == "__main__":
    unittest.main()
