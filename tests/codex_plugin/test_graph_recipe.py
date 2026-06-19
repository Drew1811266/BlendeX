import unittest

from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request
from codex_plugin.blendex_mcp.graph_recipe import (
    GraphLinkSpec,
    GraphNodeSpec,
    GraphRecipeBatch,
    GraphSocketValueSpec,
)


class GraphRecipeTests(unittest.TestCase):
    def test_graph_recipe_batch_emits_structured_operations(self):
        batch = GraphRecipeBatch(
            object_name="BlendeX Test Graph",
            nodes=[
                GraphNodeSpec(
                    client_id="join",
                    node_type="GeometryNodeJoinGeometry",
                    label="Join Result",
                    location=[0, 0],
                ),
                GraphNodeSpec(
                    client_id="transform",
                    node_type="GeometryNodeTransform",
                    label="Offset Module",
                    location=[220, 0],
                ),
            ],
            socket_values=[
                GraphSocketValueSpec(
                    node_id="transform",
                    socket="Scale",
                    value=[1.0, 2.0, 3.0],
                )
            ],
            links=[
                GraphLinkSpec(
                    from_node="transform",
                    from_socket="Geometry",
                    to_node="join",
                    to_socket="Geometry",
                )
            ],
        )

        operations = batch.to_operations()

        self.assertEqual(
            [operation["type"] for operation in operations],
            [
                "scene.create_carrier_mesh",
                "geometry_nodes.create_modifier",
                "geometry_nodes.create_node",
                "geometry_nodes.create_node",
                "geometry_nodes.set_socket_value",
                "geometry_nodes.link_sockets",
            ],
        )
        self.assertEqual(operations[0]["params"], {"name": "BlendeX Test Graph"})
        self.assertEqual(operations[1]["target"], {"object_id": "BlendeX Test Graph"})
        self.assertEqual(operations[2]["params"]["client_id"], "join")
        self.assertEqual(operations[3]["params"]["label"], "Offset Module")
        self.assertEqual(operations[4]["params"]["node_id"], "transform")
        self.assertEqual(operations[4]["params"]["value"], [1.0, 2.0, 3.0])
        self.assertEqual(operations[5]["params"]["from_node"], "transform")
        self.assertEqual(operations[5]["params"]["to_node"], "join")

        for operation in operations:
            validate_request(OperationRequest.from_dict(operation))

    def test_graph_recipe_batch_generates_stable_operation_ids(self):
        batch = GraphRecipeBatch(
            object_name="BlendeX Stable IDs",
            nodes=[
                GraphNodeSpec("join", "GeometryNodeJoinGeometry", "Join", [0, 0]),
            ],
            socket_values=[
                GraphSocketValueSpec("join", "Factor", 0.5),
            ],
            links=[
                GraphLinkSpec("join", "Geometry", "join", "Geometry"),
            ],
        )

        operation_ids = [operation["id"] for operation in batch.to_operations()]

        self.assertEqual(
            operation_ids,
            [
                "create_blendex_stable_ids",
                "create_modifier",
                "create_join",
                "set_join_factor",
                "link_join_geometry_to_join_geometry",
            ],
        )


if __name__ == "__main__":
    unittest.main()
