import unittest

from codex_plugin.blendex_mcp.workflow import confirmation_summary, confirmed_batch_arguments


class WorkflowTests(unittest.TestCase):
    def test_confirmation_summary_names_target_and_change_counts(self):
        dry_run = {
            "status": "partial",
            "preview": {
                "objects": [],
                "modifiers": [{"object_id": "Cube", "modifier_id": "BlendeX Geometry"}],
                "nodes": [{"node_type": "GeometryNodeJoinGeometry", "label": "Join"}],
                "socket_values": [{"node_id": "Join", "socket": "Value", "value": 2.0}],
                "links": [
                    {
                        "from_node": "A",
                        "from_socket": "Geometry",
                        "to_node": "B",
                        "to_socket": "Geometry",
                    }
                ],
                "labels": [],
                "warnings": [{"code": "SIMULATED_NODE_METADATA", "message": "partial metadata"}],
            },
        }

        summary = confirmation_summary(dry_run)

        self.assertIn("Cube", summary)
        self.assertIn("BlendeX Geometry", summary)
        self.assertIn("1 node", summary)
        self.assertIn("1 link", summary)
        self.assertIn("1 socket value", summary)
        self.assertIn("1 warning", summary)

    def test_confirmation_summary_handles_missing_preview_and_modifier(self):
        summary = confirmation_summary({"status": "valid"})

        self.assertIn("selected target", summary)
        self.assertIn("BlendeX Geometry", summary)
        self.assertIn("0 nodes", summary)
        self.assertIn("0 links", summary)
        self.assertIn("0 socket values", summary)

    def test_confirmed_batch_arguments_marks_confirmation_and_defaults_preview(self):
        operations = [{"id": "op", "type": "scene.inspect", "target": {}, "params": {}}]

        args = confirmed_batch_arguments(
            operations=operations,
            confirmation_id="confirm_1",
            summary="Inspect scene",
        )

        self.assertEqual(args["operations"], operations)
        self.assertTrue(args["confirmed"])
        self.assertEqual(args["confirmation_id"], "confirm_1")
        self.assertEqual(args["summary"], "Inspect scene")
        self.assertEqual(args["preview"], {})

    def test_confirmed_batch_arguments_preserves_preview(self):
        preview = {"nodes": [{"client_id": "join"}]}

        args = confirmed_batch_arguments(
            operations=[],
            confirmation_id="confirm_2",
            summary="Create node",
            preview=preview,
        )

        self.assertIs(args["preview"], preview)


if __name__ == "__main__":
    unittest.main()
