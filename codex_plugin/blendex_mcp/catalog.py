import copy
from typing import Any, Dict


SEMANTIC_NODE_CATALOG: Dict[str, Dict[str, Any]] = {
    "NodeGroupInput": {
        "role": "Provides group input geometry and exposed parameters.",
        "common_use": "Start geometry flow from the modifier input.",
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use as the first geometry source in simple pass-through graphs."],
        "common_pairings": ["NodeGroupOutput", "GeometryNodeJoinGeometry"],
    },
    "NodeGroupOutput": {
        "role": "Receives final geometry for the modifier output.",
        "common_use": "End a Geometry Nodes graph.",
        "typical_inputs": ["Geometry"],
        "planning_hints": ["Ensure exactly one final geometry flow reaches Group Output."],
        "common_pairings": ["GeometryNodeJoinGeometry", "GeometryNodeRealizeInstances"],
    },
    "GeometryNodeJoinGeometry": {
        "role": "Combines multiple geometry streams into one output.",
        "common_use": "Merge generated pieces before sending to Group Output.",
        "typical_inputs": ["Geometry"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Place near the end of graphs that combine source and generated geometry."],
        "common_pairings": ["NodeGroupOutput", "GeometryNodeInstanceOnPoints"],
    },
    "GeometryNodeInstanceOnPoints": {
        "role": "Places instances on point geometry.",
        "common_use": "Scatter repeated modules on generated or existing points.",
        "typical_inputs": ["Points", "Instance", "Selection", "Rotation", "Scale"],
        "typical_outputs": ["Instances"],
        "planning_hints": ["Realize instances before downstream mesh-only operations."],
        "common_pairings": ["GeometryNodeDistributePointsOnFaces", "GeometryNodeRealizeInstances"],
    },
    "GeometryNodeRealizeInstances": {
        "role": "Converts instances into realized geometry.",
        "common_use": "Apply downstream mesh operations after instancing.",
        "typical_inputs": ["Geometry"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use after instance-heavy sections when later nodes need real geometry."],
        "common_pairings": ["GeometryNodeInstanceOnPoints", "GeometryNodeJoinGeometry"],
    },
    "GeometryNodeSetPosition": {
        "role": "Offsets point or mesh positions.",
        "common_use": "Warp, lift, or procedurally deform geometry.",
        "typical_inputs": ["Geometry", "Selection", "Position", "Offset"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use vector math or random values to drive the Offset input."],
        "common_pairings": ["ShaderNodeVectorMath", "FunctionNodeRandomValue"],
    },
    "GeometryNodeTransform": {
        "role": "Applies translation, rotation, and scale to geometry.",
        "common_use": "Move or resize generated geometry streams.",
        "typical_inputs": ["Geometry", "Translation", "Rotation", "Scale"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Use before join nodes to arrange generated modules."],
        "common_pairings": ["GeometryNodeJoinGeometry"],
    },
    "GeometryNodeSetMaterial": {
        "role": "Assigns a material to geometry.",
        "common_use": "Apply generated or existing materials to procedural output.",
        "typical_inputs": ["Geometry", "Selection", "Material"],
        "typical_outputs": ["Geometry"],
        "planning_hints": ["Place after geometry creation and before final output."],
        "common_pairings": ["NodeGroupOutput", "GeometryNodeJoinGeometry"],
    },
    "FunctionNodeRandomValue": {
        "role": "Generates deterministic random values.",
        "common_use": "Drive varied scale, rotation, color, or offsets.",
        "typical_inputs": ["Min", "Max", "ID", "Seed"],
        "typical_outputs": ["Value"],
        "planning_hints": ["Connect to transform, scale, or selection inputs for variation."],
        "common_pairings": ["GeometryNodeInstanceOnPoints", "GeometryNodeSetPosition"],
    },
    "ShaderNodeMath": {
        "role": "Computes scalar math values.",
        "common_use": "Scale, clamp, remap, or combine numeric fields.",
        "typical_inputs": ["Value"],
        "typical_outputs": ["Value"],
        "planning_hints": ["Use for simple numeric shaping before socket values or fields."],
        "common_pairings": ["FunctionNodeRandomValue"],
    },
    "ShaderNodeVectorMath": {
        "role": "Computes vector math values.",
        "common_use": "Build offsets, directions, and vector transforms.",
        "typical_inputs": ["Vector"],
        "typical_outputs": ["Vector"],
        "planning_hints": ["Use before position or transform nodes for procedural movement."],
        "common_pairings": ["GeometryNodeSetPosition"],
    },
}


def semantic_for_node(node_type: str) -> Dict[str, Any]:
    return copy.deepcopy(SEMANTIC_NODE_CATALOG.get(node_type, {}))
