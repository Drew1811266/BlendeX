from typing import Any, Dict, List, Optional, Set


def _custom_property(modifier: Any, key: str, default: Any = None) -> Any:
    getter = getattr(modifier, "get", None)
    if callable(getter):
        return getter(key, default)
    try:
        return modifier[key]
    except (KeyError, TypeError, AttributeError):
        return default


def _modifier_summary(modifier: Any) -> Dict[str, Any]:
    modifier_type = getattr(modifier, "type", "")
    blendex_owned = bool(_custom_property(modifier, "blendex_owned", False))
    node_group = getattr(modifier, "node_group", None)
    return {
        "name": getattr(modifier, "name", ""),
        "type": modifier_type,
        "blendex_owned": blendex_owned,
        "safe_for_mutation": modifier_type == "NODES" and blendex_owned,
        "node_group": getattr(node_group, "name", None),
    }


def _object_selected(obj: Any, selected_names: Set[str]) -> bool:
    select_get = getattr(obj, "select_get", None)
    if callable(select_get):
        try:
            return bool(select_get())
        except Exception:
            pass
    return getattr(obj, "name", "") in selected_names


def _object_visible(obj: Any) -> bool:
    visible_get = getattr(obj, "visible_get", None)
    if callable(visible_get):
        try:
            return bool(visible_get())
        except Exception:
            pass
    return not bool(getattr(obj, "hide_viewport", False))


def _object_summary(obj: Any, selected_names: Set[str]) -> Dict[str, Any]:
    name = getattr(obj, "name", "")
    return {
        "id": name,
        "name": name,
        "type": getattr(obj, "type", ""),
        "selected": _object_selected(obj, selected_names),
        "visible": _object_visible(obj),
        "modifiers": [_modifier_summary(modifier) for modifier in getattr(obj, "modifiers", [])],
    }


def _recommended_target(
    objects: List[Dict[str, Any]],
    selected_object: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not selected_object:
        return None
    for obj in objects:
        if obj.get("id") != selected_object:
            continue
        for modifier in obj.get("modifiers", []):
            if modifier.get("safe_for_mutation"):
                return {
                    "object_id": obj["id"],
                    "modifier_id": modifier.get("name", ""),
                    "reason": "selected_blendex_modifier",
                }
        if obj.get("type") == "MESH":
            return {
                "object_id": obj["id"],
                "reason": "selected_mesh_without_blendex_modifier",
            }
    return None


def _version_list(version: Any) -> Optional[List[int]]:
    if version is None:
        return None
    try:
        return list(version)
    except TypeError:
        return None


def inspect_scene(context: Any) -> Dict[str, Any]:
    selected_objects = list(getattr(context, "selected_objects", []) or [])
    selected_names = {getattr(obj, "name", "") for obj in selected_objects}
    active_object = getattr(context, "object", None)
    selected_object = getattr(active_object, "name", None) if active_object is not None else None
    objects = [_object_summary(obj, selected_names) for obj in getattr(context, "objects", [])]
    result = {
        "objects": objects,
        "selected_objects": sorted(name for name in selected_names if name),
        "selected_object": selected_object,
        "recommended_target": _recommended_target(objects, selected_object),
    }
    version = _version_list(getattr(context, "version", None))
    if version is not None:
        result["blender_version"] = version
    return result


def _select_object(context: Any, obj: Any) -> None:
    select_object = getattr(context, "select_object", None)
    if callable(select_object):
        select_object(obj)
        return
    for existing in getattr(context, "objects", []) or []:
        select_set = getattr(existing, "select_set", None)
        if callable(select_set):
            try:
                select_set(False)
            except Exception:
                pass
    select_set = getattr(obj, "select_set", None)
    if callable(select_set):
        try:
            select_set(True)
        except Exception:
            pass
    try:
        context.selected_objects = [obj]
    except Exception:
        pass


def _set_active_object(context: Any, obj: Any) -> None:
    set_active_object = getattr(context, "set_active_object", None)
    if callable(set_active_object):
        set_active_object(obj)
        return
    try:
        context.object = obj
    except Exception:
        pass


def create_carrier_mesh(context: Any, name: str = "BlendeX Carrier") -> Dict[str, Any]:
    factory = getattr(context, "create_mesh_object", None)
    if callable(factory):
        obj = factory(name)
    else:
        import bpy

        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
    obj.name = name
    _select_object(context, obj)
    _set_active_object(context, obj)
    active_object = getattr(context, "object", None)
    selected_object = getattr(active_object, "name", getattr(obj, "name", None))
    return {
        "object_id": getattr(obj, "name", name),
        "name": getattr(obj, "name", name),
        "selected_object": selected_object,
    }


class _BpySceneContext:
    def __init__(self, bpy_module: Any):
        self._bpy = bpy_module
        self.version = getattr(getattr(bpy_module, "app", None), "version", None)

    @property
    def objects(self) -> Any:
        return self._bpy.data.objects

    @property
    def selected_objects(self) -> Any:
        return getattr(self._bpy.context, "selected_objects", [])

    @selected_objects.setter
    def selected_objects(self, _value: Any) -> None:
        pass

    @property
    def object(self) -> Any:
        return getattr(self._bpy.context, "object", None)

    @object.setter
    def object(self, obj: Any) -> None:
        self.set_active_object(obj)

    def create_mesh_object(self, name: str) -> Any:
        self._bpy.ops.mesh.primitive_cube_add(size=1)
        obj = self._bpy.context.object
        obj.name = name
        return obj

    def select_object(self, obj: Any) -> None:
        for existing in self.objects:
            select_set = getattr(existing, "select_set", None)
            if callable(select_set):
                try:
                    select_set(False)
                except Exception:
                    pass
        select_set = getattr(obj, "select_set", None)
        if callable(select_set):
            select_set(True)

    def set_active_object(self, obj: Any) -> None:
        view_layer = getattr(getattr(self._bpy, "context", None), "view_layer", None)
        view_layer_objects = getattr(view_layer, "objects", None)
        try:
            view_layer_objects.active = obj
        except Exception:
            pass


def bpy_scene_context() -> Any:
    import bpy

    return _BpySceneContext(bpy)
