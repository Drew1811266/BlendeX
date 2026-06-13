import unittest

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest

from blender_addon.blendex.batches import execute_batch
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


class BatchExecutionTests(unittest.TestCase):
    def setUp(self):
        STATE.batch_history.records.clear()

    def test_execute_batch_records_results_and_resolves_client_ids(self):
        executor = RecordingExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": {
                    "summary": "Create and link nodes",
                    "operations": [
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
                },
            },
            executor,
        )

        self.assertNotIn("confirmed", result)
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
                "params": {
                    "summary": "Audit metadata",
                    "dry_run": True,
                    "actor": "codex",
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
            params={"operations": []},
        )

        with self.assertRaises(BlendexError) as raised:
            execute_batch(request, executor)

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(executor.requests, [])
        self.assertIsNone(STATE.batch_history.latest())

    def test_execute_batch_continues_after_failure_and_records_partial_status(self):
        executor = RecordingExecutor(fail_on={"bad_node"})
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": {
                    "operations": [
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
                },
            },
            executor,
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["operations"][0]["ok"], True)
        self.assertEqual(result["operations"][1]["ok"], False)
        self.assertEqual(result["error"]["code"], "NODE_TYPE_NOT_FOUND")
        self.assertEqual(STATE.batch_history.latest().status, "partial")

    def test_failed_create_does_not_fall_through_to_existing_node_matching_client_id(self):
        executor = ExistingNodeExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": {
                    "operations": [
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
                },
            },
            executor,
        )

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["operations"][0]["ok"])
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][1]["error"]["code"], "EXECUTION_FAILED")
        self.assertEqual(executor.node_labels["join"], "Existing Label")
        self.assertEqual([request.id for request in executor.requests], ["make_join"])

    def test_generic_executor_exception_records_failed_partial_batch(self):
        executor = RuntimeFailingExecutor()
        result = execute_batch(
            {
                "target": {"object_id": "Cube"},
                "params": {
                    "operations": [
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
                },
            },
            executor,
        )

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["operations"][0]["ok"])
        self.assertFalse(result["operations"][1]["ok"])
        self.assertEqual(result["operations"][1]["error"]["code"], "EXECUTION_FAILED")
        self.assertEqual(STATE.batch_history.latest().batch_id, result["batch_id"])
        self.assertEqual(STATE.batch_history.latest().status, "partial")

    def test_execute_batch_rejects_duplicate_client_ids_before_running_operations(self):
        executor = RecordingExecutor()

        with self.assertRaises(BlendexError) as raised:
            execute_batch(
                {
                    "target": {"object_id": "Cube"},
                    "params": {
                        "operations": [
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
                    },
                },
                executor,
            )

        self.assertEqual(raised.exception.code, "VALIDATION_FAILED")
        self.assertEqual(executor.requests, [])


if __name__ == "__main__":
    unittest.main()
