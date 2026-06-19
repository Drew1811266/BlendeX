from typing import Any, Dict, List, Optional


def _list_count(preview: Dict[str, Any], key: str) -> int:
    value = preview.get(key, [])
    return len(value) if isinstance(value, list) else 0


def _plural(count: int, label: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count} {label}{suffix}"


def _safe_count(value: Any, fallback: int) -> int:
    return value if isinstance(value, int) and value >= 0 else fallback


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
    summary = dry_run_result.get("summary")
    if isinstance(summary, dict) and summary:
        target = summary.get("target", {})
        if isinstance(target, dict):
            object_id = target.get("object_id")
            modifier_id = target.get("modifier_id")
            object_id = object_id if isinstance(object_id, str) and object_id else "selected target"
            modifier_id = modifier_id if isinstance(modifier_id, str) and modifier_id else "BlendeX Geometry"
        else:
            object_id, modifier_id = _target_from_preview(preview)
        changes = summary.get("changes", {})
        if isinstance(changes, dict):
            node_count = _safe_count(changes.get("nodes"), _list_count(preview, "nodes"))
            link_count = _safe_count(changes.get("links"), _list_count(preview, "links"))
            socket_value_count = _safe_count(changes.get("socket_values"), _list_count(preview, "socket_values"))
        else:
            node_count = _list_count(preview, "nodes")
            link_count = _list_count(preview, "links")
            socket_value_count = _list_count(preview, "socket_values")
        warning_count = summary.get("warnings", _list_count(preview, "warnings"))
        warning_count = warning_count if isinstance(warning_count, int) else _list_count(preview, "warnings")
        requires_confirmation = summary.get("requires_confirmation")
    else:
        object_id, modifier_id = _target_from_preview(preview)
        node_count = _list_count(preview, "nodes")
        link_count = _list_count(preview, "links")
        socket_value_count = _list_count(preview, "socket_values")
        warning_count = _list_count(preview, "warnings")
        requires_confirmation = dry_run_result.get("status") in {"valid", "partial"}
    status = dry_run_result.get("status", "unknown")
    status = status if isinstance(status, str) and status else "unknown"
    parts = [
        f"Dry run: {status}",
        f"Target: {object_id} / {modifier_id}",
        _plural(node_count, "node"),
        _plural(link_count, "link"),
        _plural(socket_value_count, "socket value"),
    ]
    if warning_count:
        parts.append(_plural(warning_count, "warning"))
    if requires_confirmation:
        parts.append("requires confirmation")
    return "; ".join(parts)


def confirmed_batch_arguments(
    operations: List[Dict[str, Any]],
    confirmation_id: str,
    summary: str,
    preview: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "operations": operations,
        "confirmation_id": confirmation_id,
        "summary": summary,
        "preview": preview or {},
    }
