import json
import unittest

from blender_addon.blendex.history import BatchHistory, BatchRecord


class BatchHistoryTests(unittest.TestCase):
    def test_recent_returns_newest_first_and_honors_limit(self):
        history = BatchHistory(max_batches=2)
        first = BatchRecord(
            batch_id="batch_first",
            status="succeeded",
            operation_count=1,
            target={"object_id": "Cube"},
            summary="First",
            operations=[],
            preview={},
            timestamp=1.0,
        )
        second = BatchRecord(
            batch_id="batch_second",
            status="failed",
            operation_count=1,
            target={"object_id": "Cube"},
            summary="Second",
            operations=[],
            preview={},
            timestamp=2.0,
        )
        third = BatchRecord(
            batch_id="batch_third",
            status="partial",
            operation_count=2,
            target={"object_id": "Cube"},
            summary="Third",
            operations=[],
            preview={},
            timestamp=3.0,
        )

        history.record(first)
        history.record(second)
        history.record(third)

        self.assertEqual([record.batch_id for record in history.recent()], ["batch_third", "batch_second"])
        self.assertEqual(history.latest().batch_id, "batch_third")
        self.assertIsNone(history.find("batch_first"))
        self.assertEqual(history.find("batch_second").batch_id, "batch_second")

    def test_batch_record_to_dict_is_json_safe(self):
        record = BatchRecord(
            batch_id="batch_json",
            status="succeeded",
            operation_count=1,
            target={"object_id": "Cube"},
            summary="Created one node",
            operations=[{"id": "op_1", "ok": True, "result": {"node_id": "Node.001"}}],
            preview={"nodes": [{"client_id": "noise", "node_id": "Node.001"}]},
            timestamp=42.5,
            dry_run=True,
            actor="codex",
            confirmation_id="confirm_json",
        )

        payload = record.to_dict()

        self.assertEqual(payload["batch_id"], "batch_json")
        self.assertEqual(payload["confirmation_id"], "confirm_json")
        self.assertEqual(payload["dry_run"], True)
        self.assertEqual(payload["actor"], "codex")
        self.assertEqual(payload["undo_status"], "not_requested")
        self.assertIsNone(payload["error"])
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
