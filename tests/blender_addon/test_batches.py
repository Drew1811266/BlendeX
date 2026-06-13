import unittest

from blendex_protocol.errors import BlendexError

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

        self.assertTrue(result["confirmed"])
        self.assertTrue(result["batch_id"].startswith("batch_"))
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual([entry["id"] for entry in result["operations"]], ["make_noise", "link_noise"])
        self.assertEqual(executor.requests[1].params["from_node"], "runtime_noise")
        self.assertEqual(result["operations"][1]["result"]["from_node"], "runtime_noise")
        self.assertEqual(STATE.batch_history.latest().batch_id, result["batch_id"])

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


if __name__ == "__main__":
    unittest.main()
