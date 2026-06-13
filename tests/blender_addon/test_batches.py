import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest

from blender_addon.blendex.batches import execute_batch, undo_last_batch
from blender_addon.blendex.state import STATE


class RecordingExecutor:
    def __init__(self, fail_on=None):
        self.requests = []
        self.fail_on = fail_on or set()

    def execute(self, request):
        self.requests.append(request)
        if request.id in self.fail_on:
            raise BlendexError("NODE_TYPE_NOT_FOUND", "missing test node")
        if request.type == "geometry_nodes.create_node":
            return {"id": f"runtime_{request.params['client_id']}", "label": request.params.get("label", "")}
        if request.type == "geometry_nodes.link_sockets":
            return {
                "from_node": request.params["from_node"],
                "from_socket": request.params["from_socket"],
                "to_node": request.params["to_node"],
                "to_socket": request.params["to_socket"],
            }
        return {"ok": True}


class ExistingNodeExecutor:
    def __init__(self):
        self.requests = []
        self.node_labels = {"join": "Existing Label"}

    def execute(self, request):
        self.requests.append(request)
        if request.id == "make_join":
            raise BlendexError("NODE_TYPE_NOT_FOUND", "missing test node")
        if request.type == "geometry_nodes.label_node":
            self.node_labels[request.params["node_id"]] = request.params["label"]
            return {"node_id": request.params["node_id"], "label": request.params["label"]}
        return {"ok": True}


class RuntimeFailingExecutor(RecordingExecutor):
    def execute(self, request):
        if request.id == "boom":
            raise RuntimeError("Blender exploded")
        return super().execute(request)


def _confirmed_params(operations, summary="Confirmed test batch", confirmation_id="confirm_test", **extra):
    return {
        "confirmed": True,
        "confirmation_id": confirmation_id,
        "summary": summary,
        "operations": operations,
        **extra,
    }


class BatchExecutionTests(unittest.TestCase):
    def setUp(self):
        STATE.batch_history.records.clear()
        STATE.undo_callback = None

    def test_execute_batch_records_results_and_resolves_client_ids(self):
        executor = RecordingExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "make_noise",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        },
                        {
                            "id": "link_noise",
                            "type": "geometry_nodes.link_sockets",
                            "target": {"object_id": "Cube"},
                            "params": {
                                "from_node": "noise",
                                "from_socket": "Fac",
                                "to_node": "Group Output",
                                "to_socket": "Geometry",
                            },
                        },
                    ],
                    summary="Create and link nodes",
                    confirmation_id="confirm_create_link",
                ),
            },
            executor,
        )

        self.assertNotIn("confirmed", result)
        self.assertEqual(result["confirmation_id"], "confirm_create_link")
        self.assertTrue(result["batch_id"].startswith("batch_"))
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual([entry["id"] for entry in result["operations"]], ["make_noise", "link_noise"])
        self.assertEqual(executor.requests[1].params["from_node"], "runtime_noise")
        self.assertEqual(result["operations"][1]["result"]["from_node"], "runtime_noise")
        self.assertEqual(STATE.batch_history.latest().batch_id, result["batch_id"])

    def test_execute_batch_records_dry_run_and_actor_metadata(self):
        executor = RecordingExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "make_noise",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                    summary="Audit metadata",
                    confirmation_id="confirm_metadata",
                    dry_run=True,
                    actor="codex",
                ),
            },
            executor,
        )

        self.assertEqual(result["dry_run"], True)
        self.assertEqual(result["actor"], "codex")
        self.assertEqual(STATE.batch_history.latest().dry_run, True)
        self.assertEqual(STATE.batch_history.latest().actor, "codex")
        self.assertEqual(STATE.batch_history.latest().to_dict()["dry_run"], True)
        self.assertEqual(STATE.batch_history.latest().to_dict()["actor"], "codex")

    def test_execute_batch_rejects_empty_operations_without_recording_history(self):
        executor = RecordingExecutor()
        request = OperationRequest(
            id="req_empty_batch",
            type="safety.execute_batch",
            target={"object_id": "Cube"},
            params=_confirmed_params([], summary="Empty batch", confirmation_id="confirm_empty"),
        )

        with self.assertRaises(BlendexError) as raised:
            execute_batch(request, executor)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(executor.requests, [])
        self.assertIsNone(STATE.batch_history.latest())

    def test_execute_batch_requires_confirmation_before_mutation_or_history(self):
        executor = RecordingExecutor()

        with self.assertRaises(BlendexError) as raised:
            execute_batch(
                {
                    "target": {"object_id": "Cube"},
                    "params": {
                        "summary": "Unconfirmed node",
                        "operations": [
                            {
                                "id": "make_noise",
                                "type": "geometry_nodes.create_node",
                                "target": {"object_id": "Cube"},
                                "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                            }
                        ],
                    },
                },
                executor,
            )

        self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
        self.assertEqual(executor.requests, [])
        self.assertIsNone(STATE.batch_history.latest())

    def test_execute_batch_preserves_confirmation_id(self):
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "make_noise",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                    summary="Create node",
                    confirmation_id="confirm_preserved",
                ),
            },
            RecordingExecutor(),
        )

        self.assertEqual(result["confirmation_id"], "confirm_preserved")
        self.assertEqual(STATE.batch_history.latest().confirmation_id, "confirm_preserved")
        self.assertEqual(STATE.batch_history.latest().to_dict()["confirmation_id"], "confirm_preserved")

    def test_execute_batch_continues_after_failure_and_records_partial_status(self):
        executor = RecordingExecutor(fail_on={"bad_node"})
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        },
                        {
                            "id": "bad_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeMissing", "client_id": "missing"},
                        },
                    ],
                ),
            },
            executor,
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["operations"][0]["ok"], True)
        self.assertEqual(result["operations"][1]["ok"], False)
        self.assertEqual(result["error"]["code"], "NODE_TYPE_NOT_FOUND")
        self.assertEqual(result["error"]["mutation_occurred"], True)
        self.assertEqual(result["error"]["batch_id"], result["batch_id"])
        self.assertEqual(result["operations"][1]["error"]["mutation_occurred"], True)
        self.assertEqual(result["operations"][1]["error"]["batch_id"], result["batch_id"])
        self.assertEqual(STATE.batch_history.latest().status, "partial")

    def test_failed_create_does_not_fall_through_to_existing_node_matching_client_id(self):
        executor = ExistingNodeExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "make_join",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeMissing", "client_id": "join"},
                        },
                        {
                            "id": "label_join",
                            "type": "geometry_nodes.label_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_id": "join", "label": "Should Not Mutate"},
                        },
                    ],
                ),
            },
            executor,
        )

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["operations"][0]["ok"])
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][0]["error"]["mutation_occurred"], False)
        self.assertEqual(result["operations"][1]["error"]["mutation_occurred"], False)
        self.assertNotIn("batch_id", result["operations"][0]["error"])
        self.assertNotIn("batch_id", result["operations"][1]["error"])
        self.assertEqual(result["operations"][1]["error"]["code"], "EXECUTION_FAILED")
        self.assertEqual(executor.node_labels["join"], "Existing Label")
        self.assertEqual([request.id for request in executor.requests], ["make_join"])

    def test_generic_executor_exception_records_failed_partial_batch(self):
        executor = RuntimeFailingExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        },
                        {
                            "id": "boom",
                            "type": "geometry_nodes.label_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_id": "noise", "label": "Nope"},
                        },
                    ],
                ),
            },
            executor,
        )

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["operations"][0]["ok"])
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][1]["error"]["code"], "EXECUTION_FAILED")
        self.assertEqual(result["operations"][1]["error"]["mutation_occurred"], True)
        self.assertEqual(result["operations"][1]["error"]["batch_id"], result["batch_id"])
        self.assertEqual(STATE.batch_history.latest().batch_id, result["batch_id"])
        self.assertEqual(STATE.batch_history.latest().status, "partial")

    def test_execute_batch_rejects_duplicate_client_ids_before_running_operations(self):
        executor = RecordingExecutor()

        with self.assertRaises(BlendexError) as raised:
            execute_batch(
                {
                    "target": {"object_id": "Cube"},
                    "params": _confirmed_params(
                        [
                            {
                                "id": "first",
                                "type": "geometry_nodes.create_node",
                                "target": {"object_id": "Cube"},
                                "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                            },
                            {
                                "id": "second",
                                "type": "geometry_nodes.create_node",
                                "target": {"object_id": "Cube"},
                                "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                            },
                        ],
                    ),
                },
                executor,
            )

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(executor.requests, [])

    def test_undo_last_batch_marks_latest_batch_undone(self):
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                ),
            },
            RecordingExecutor(),
        )

        undo_result = undo_last_batch()

        self.assertEqual(undo_result["batch_id"], result["batch_id"])
        self.assertEqual(undo_result["undo_status"], "undone")
        self.assertIsNone(undo_result["undo_error"])
        self.assertEqual(STATE.batch_history.latest().undo_status, "undone")

    def test_undo_last_batch_raises_when_history_is_empty(self):
        with self.assertRaises(BlendexError) as raised:
            undo_last_batch()

        self.assertEqual(raised.exception.code, "UNDO_UNAVAILABLE")
        self.assertEqual(raised.exception.message, "No BlendeX batch is available to undo.")

    def test_undo_last_batch_marks_failed_latest_batch_unavailable(self):
        execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "bad_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeMissing", "client_id": "missing"},
                        }
                    ],
                ),
            },
            RecordingExecutor(fail_on={"bad_node"}),
        )

        with self.assertRaises(BlendexError) as raised:
            undo_last_batch()

        latest = STATE.batch_history.latest()
        self.assertEqual(raised.exception.code, "UNDO_UNAVAILABLE")
        self.assertEqual(latest.undo_status, "unavailable")
        self.assertEqual(latest.undo_error["code"], "UNDO_UNAVAILABLE")
        self.assertEqual(latest.to_dict()["undo_error"]["code"], "UNDO_UNAVAILABLE")

    def test_undo_last_batch_is_idempotent_when_already_undone(self):
        execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                ),
            },
            RecordingExecutor(),
        )
        STATE.batch_history.latest().undo_status = "undone"

        undo_result = undo_last_batch()

        self.assertEqual(undo_result["undo_status"], "undone")

    def test_undo_last_batch_invokes_optional_callback_with_batch(self):
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                ),
            },
            RecordingExecutor(),
        )
        callback_batches = []
        STATE.undo_callback = callback_batches.append

        undo_result = undo_last_batch()

        self.assertEqual(undo_result["batch_id"], result["batch_id"])
        self.assertEqual([batch.batch_id for batch in callback_batches], [result["batch_id"]])

    def test_undo_last_batch_preserves_blendex_callback_error(self):
        execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                ),
            },
            RecordingExecutor(),
        )

        def fail_undo(batch):
            raise BlendexError("EXECUTION_FAILED", "undo callback failed")

        STATE.undo_callback = fail_undo

        with self.assertRaises(BlendexError) as raised:
            undo_last_batch()

        latest = STATE.batch_history.latest()
        self.assertEqual(raised.exception.code, "EXECUTION_FAILED")
        self.assertEqual(latest.undo_status, "failed")
        self.assertEqual(latest.undo_error["message"], "undo callback failed")

    def test_undo_last_batch_wraps_generic_callback_error(self):
        execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": _confirmed_params(
                    [
                        {
                            "id": "good_node",
                            "type": "geometry_nodes.create_node",
                            "target": {"object_id": "Cube"},
                            "params": {"node_type": "GeometryNodeTexNoise", "client_id": "noise"},
                        }
                    ],
                ),
            },
            RecordingExecutor(),
        )

        def fail_undo(batch):
            raise RuntimeError("native undo failed")

        STATE.undo_callback = fail_undo

        with self.assertRaises(BlendexError) as raised:
            undo_last_batch()

        latest = STATE.batch_history.latest()
        self.assertEqual(raised.exception.code, "UNDO_FAILED")
        self.assertEqual(latest.undo_status, "failed")
        self.assertEqual(latest.undo_error["message"], "native undo failed")


if __name__ == "__main__":
    unittest.main()
