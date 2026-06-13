from typing import Any, Dict, List, Optional


def _list_count(preview: Dict[str, Any], key: str) -> int:
    value = preview.get(key, [])
    return len(value) if isinstance(value, list) else 0


def _plural(count: int, label: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count} {label}{suffix}"


def _target_from_preview(preview: Dict[str, Any]) -> tuple[str, str]:
    modifiers = preview.get("modifiers", [])
    if isinstance(modifiers, list) and modifiers:
        first_modifier = modifiers[0]
        if isinstance(first_modifier, dict):
            object_id = first_modifier.get("object_id")
            modifier_id = first_modifier.get("modifier_id")
            return (
                object_id if isinstance(object_id, str) and object_id else "selected target",
                modifier_id if isinstance(modifier_id, str) and modifier_id else "BlendeX Geometry",
            )
    nodes = preview.get("nodes", [])
    if isinstance(nodes, list) and nodes:
        first_node = nodes[0]
        if isinstance(first_node, dict):
            object_id = first_node.get("object_id")
            modifier_id = first_node.get("modifier_id")
            return (
                object_id if isinstance(object_id, str) and object_id else "selected target",
                modifier_id if isinstance(modifier_id, str) and modifier_id else "BlendeX Geometry",
            )
    return "selected target", "BlendeX Geometry"


def confirmation_summary(dry_run_result: Dict[str, Any]) -> str:
    preview = dry_run_result.get("preview", {})
    if not isinstance(preview, dict):
        preview = {}
    object_id, modifier_id = _target_from_preview(preview)
    parts = [
        f"Target: {object_id} / {modifier_id}",
        _plural(_list_count(preview, "nodes"), "node"),
        _plural(_list_count(preview, "links"), "link"),
        _plural(_list_count(preview, "socket_values"), "socket value"),
    ]
    warning_count = _list_count(preview, "warnings")
    if warning_count:
        parts.append(_plural(warning_count, "warning"))
    return "; ".join(parts)


def confirmed_batch_arguments(
    operations: List[Dict[str, Any]],
    confirmation_id: str,
    summary: str,
    preview: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "operations": operations,
        "confirmed": True,
        "confirmation_id": confirmation_id,
        "summary": summary,
        "preview": preview or {},
    }
