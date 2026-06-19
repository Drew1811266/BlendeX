from typing import Any, Dict

from .node_semantics import legacy_semantic_for_node


def semantic_for_node(node_type: str) -> Dict[str, Any]:
    return legacy_semantic_for_node(node_type)
