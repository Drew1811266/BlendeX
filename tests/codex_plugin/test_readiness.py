import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class ReadinessAuditTests(unittest.TestCase):
    def test_readiness_audit_declares_v0_5_reasoning_ready_scope(self):
        audit = (ROOT / "docs" / "readiness-audit-v0.5.md").read_text()

        self.assertIn("BlendeX v0.5 Readiness Audit", audit)
        self.assertIn("Status: Ready for semantic Geometry Nodes reasoning", audit)
        self.assertIn("Version: 0.50.0", audit)
        self.assertIn("held-out benchmark: 20/20 valid graph plans", audit)
        self.assertIn("property pass: 20/20", audit)
        self.assertIn("Anti-Template Requirement: satisfied", audit)
        self.assertIn("MCP probe OK", audit)
        for capability in (
            "intent parsing",
            "node semantics",
            "typed graph IR",
            "static validation",
            "repair loop",
            "advanced fields",
            "attributes",
            "instances",
            "group inputs",
        ):
            self.assertIn(capability, audit)


if __name__ == "__main__":
    unittest.main()
