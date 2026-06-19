from typing import Any, Dict

from blendex_protocol.errors import BlendexError
from blendex_protocol.messages import OperationRequest
from blendex_protocol.validation import validate_request


class GeometryNodesExecutor:
    def __init__(self, context: Any):
        self.context = context

    def execute(self, request: OperationRequest) -> Dict[str, Any]:
        validate_request(request)
        if request.type == "geometry_nodes.create_modifier":
            return self._create_modifier(request)
        if request.type == "geometry_nodes.create_node":
            return self._create_node(request)
        if request.type == "geometry_nodes.inspect_tree":
            return self._inspect_tree(request)
        if request.type == "geometry_nodes.link_sockets":
            return self._link_sockets(request)
        if request.type == "geometry_nodes.set_socket_value":
            return self._set_socket_value(request)
        if request.type == "geometry_nodes.label_node":
            return self._label_node(request)
        if request.type == "geometry_nodes.mark_ownership":
            return self._mark_ownership(request)
        raise BlendexError(
            "UNSUPPORTED_OPERATION",
            f"Executor does not implement operation: {request.type}",
            retry_hint="Call capabilities.supported_operations before planning.",
        )

    def validate(self, request: OperationRequest) -> Dict[str, Any]:
        validate_request(request)
        if request.type == "geometry_nodes.create_modifier":
            obj = self._object(request.target["object_id"])
            modifier_id = request.params.get("modifier_id", "BlendeX Geometry")
            if self._collection_get(obj.modifiers, modifier_id) is not None:
                self._modifier(obj, modifier_id)
            return {"validated": True}
        if request.type == "geometry_nodes.create_node":
            node_type = request.params["node_type"]
            if node_type not in self.context.node_types:
                raise BlendexError(
                    "NODE_TYPE_NOT_FOUND",
                    f"Node type is unavailable: {node_type}",
                    retry_hint="Refresh capabilities and choose a node type reported by Blender.",
                )
            obj = self._object(request.target["object_id"])
            self._modifier(
                obj,
                request.target.get("modifier_id", "BlendeX Geometry"),
                require_ownership=True,
            )
            return {"validated": True}
        if request.type == "geometry_nodes.inspect_tree":
            obj = self._object(request.target["object_id"])
            modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
            self._existing_node_tree(modifier)
            return {"validated": True}
        if request.type == "geometry_nodes.link_sockets":
            self._validate_link_sockets(request)
            return {"validated": True}
        if request.type == "geometry_nodes.set_socket_value":
            self._validate_set_socket_value(request)
            return {"validated": True}
        if request.type == "geometry_nodes.label_node":
            obj = self._object(request.target["object_id"])
            modifier = self._modifier(
                obj,
                request.target.get("modifier_id", "BlendeX Geometry"),
                require_ownership=True,
            )
            tree = self._existing_node_tree(modifier)
            self._node(tree, request.params["node_id"])
            return {"validated": True}
        if request.type == "geometry_nodes.mark_ownership":
            obj = self._object(request.target["object_id"])
            self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
            return {"validated": True}
        return {"validated": True}

    def _object(self, object_id: str) -> Any:
        obj = self._collection_get(self.context.objects, object_id)
        if obj is None:
            raise BlendexError("OBJECT_NOT_FOUND", f"Object not found: {object_id}")
        return obj

    def _modifier(self, obj: Any, modifier_id: str, require_ownership: bool = False) -> Any:
        modifier = self._collection_get(obj.modifiers, modifier_id)
        if modifier is None:
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier not found: {modifier_id}")
        if self._modifier_type(modifier) != "NODES":
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier is not a Geometry Nodes modifier: {modifier_id}")
        if require_ownership:
            self._require_owned_graph(modifier, modifier_id)
        return modifier

    def _modifier_name(self, modifier: Any) -> str:
        if isinstance(modifier, dict):
            return modifier.get("name", "")
        return getattr(modifier, "name", "")

    def _modifier_type(self, modifier: Any) -> str:
        if isinstance(modifier, dict):
            return modifier.get("type", "")
        return getattr(modifier, "type", "")

    def _custom_property(self, item: Any, key: str, default: Any = None) -> Any:
        if item is None:
            return default
        if isinstance(item, dict):
            return item.get(key, default)
        getter = getattr(item, "get", None)
        if callable(getter):
            try:
                return getter(key, default)
            except TypeError:
                try:
                    value = getter(key)
                except Exception:
                    return default
                return default if value is None else value
        try:
            return item[key]
        except (KeyError, TypeError, AttributeError):
            return getattr(item, key, default)

    def _set_blendex_owned(self, item: Any) -> None:
        if item is None:
            return
        try:
            item["blendex_owned"] = True
            return
        except Exception:
            pass
        try:
            setattr(item, "blendex_owned", True)
        except Exception:
            pass

    def _is_blendex_owned(self, modifier: Any) -> bool:
        return bool(self._custom_property(modifier, "blendex_owned", False))

    def _require_owned_graph(self, modifier: Any, modifier_id: str) -> None:
        if not self._is_blendex_owned(modifier):
            raise BlendexError(
                "OWNERSHIP_REQUIRED",
                f"Modifier is not marked as BlendeX-owned: {modifier_id}",
                retry_hint="Inspect the tree first or create/use a BlendeX-owned Geometry Nodes modifier.",
            )
        tree = self._raw_node_tree(modifier)
        if tree is not None and not self._is_blendex_owned(tree):
            raise BlendexError(
                "OWNERSHIP_REQUIRED",
                f"Node group is not marked as BlendeX-owned: {getattr(tree, 'name', modifier_id)}",
                retry_hint="Create or mark a BlendeX-owned Geometry Nodes modifier before mutating.",
            )

    def _collection_get(self, collection: Any, key: str) -> Any:
        if collection is None:
            return None
        if isinstance(collection, dict):
            return collection.get(key)
        getter = getattr(collection, "get", None)
        if callable(getter):
            try:
                value = getter(key)
            except Exception:
                value = None
            if value is not None:
                return value
        try:
            iterator = iter(collection)
        except TypeError:
            return None
        for item in iterator:
            if isinstance(item, dict):
                if item.get("id") == key or item.get("name") == key:
                    return item
                continue
            if getattr(item, "name", None) == key or getattr(item, "identifier", None) == key:
                return item
        return None

    def _node(self, tree: Any, node_id: str) -> Any:
        node = self._collection_get(getattr(tree, "nodes", None), node_id)
        if node is None:
            raise BlendexError("NODE_TYPE_NOT_FOUND", f"Node not found: {node_id}")
        return node

    def _socket(self, node: Any, socket_name: str, direction: str) -> Any:
        sockets = node.get(direction, []) if isinstance(node, dict) else getattr(node, direction, [])
        socket = self._collection_get(sockets, socket_name)
        if socket is None:
            raise BlendexError(
                "SOCKET_NOT_FOUND",
                f"Socket not found: {socket_name}",
                details={"node_id": self._node_id(node), "direction": direction},
            )
        return socket

    def _node_id(self, node: Any) -> str:
        if isinstance(node, dict):
            return node.get("id") or node.get("name") or ""
        return getattr(node, "name", getattr(node, "identifier", ""))

    def _socket_name(self, socket: Any) -> str:
        if isinstance(socket, dict):
            return socket.get("name") or socket.get("identifier") or ""
        return getattr(socket, "name", getattr(socket, "identifier", ""))

    def _socket_type(self, socket: Any) -> str:
        if isinstance(socket, dict):
            return (
                socket.get("socket_type")
                or socket.get("bl_socket_idname")
                or socket.get("bl_idname")
                or socket.get("type")
                or ""
            )
        for attribute in ("bl_socket_idname", "bl_idname", "socket_type", "type"):
            value = getattr(socket, attribute, None)
            if value:
                return value
        return socket.__class__.__name__

    def _json_safe_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            return {str(key): self._json_safe_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe_value(item) for item in value]
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="replace")
        try:
            iterator = iter(value)
        except TypeError:
            return str(value)
        return [self._json_safe_value(item) for item in iterator]

    def _inspect_socket(self, socket: Any) -> Dict[str, Any]:
        if isinstance(socket, dict):
            summary = {
                "name": socket.get("name", socket.get("identifier", "")),
                "identifier": socket.get("identifier", socket.get("name", "")),
                "socket_type": self._socket_type(socket),
            }
            if "default_value" in socket:
                summary["has_default"] = True
                summary["default_value"] = self._json_safe_value(socket["default_value"])
            return summary

        summary = {
            "name": getattr(socket, "name", getattr(socket, "identifier", "")),
            "identifier": getattr(socket, "identifier", getattr(socket, "name", "")),
            "socket_type": self._socket_type(socket),
        }
        try:
            default_value = getattr(socket, "default_value")
        except Exception:
            return summary
        summary["has_default"] = True
        summary["default_value"] = self._json_safe_value(default_value)
        return summary

    def _inspect_node(self, node: Any) -> Dict[str, Any]:
        if isinstance(node, dict):
            summary = dict(node)
            summary.setdefault("id", summary.get("name", ""))
            summary.setdefault("node_type", summary.get("bl_idname", summary.get("type", "")))
            if "inputs" in summary:
                summary["inputs"] = [self._inspect_socket(socket) for socket in summary["inputs"]]
            if "outputs" in summary:
                summary["outputs"] = [self._inspect_socket(socket) for socket in summary["outputs"]]
            return summary

        label = getattr(node, "label", "")
        location = getattr(node, "location", None)
        summary = {
            "id": self._node_id(node),
            "node_type": getattr(node, "bl_idname", getattr(node, "type", "")),
            "label": label,
        }
        if location is not None:
            summary["location"] = list(location)
        summary["inputs"] = [self._inspect_socket(socket) for socket in getattr(node, "inputs", [])]
        summary["outputs"] = [self._inspect_socket(socket) for socket in getattr(node, "outputs", [])]
        return summary

    def _iter_nodes(self, tree: Any) -> list:
        nodes = getattr(tree, "nodes", {})
        if hasattr(nodes, "values"):
            return list(nodes.values())
        return list(nodes)

    def _modifier_summary(self, object_id: str, modifier: Any, tree: Any) -> Dict[str, Any]:
        modifier_id = self._modifier_name(modifier)
        node_group_id = getattr(tree, "name", None)
        modifier_owned = self._is_blendex_owned(modifier)
        tree_owned = self._is_blendex_owned(tree)
        return {
            "object_id": object_id,
            "modifier_id": modifier_id,
            "modifier_type": self._modifier_type(modifier),
            "node_group_id": node_group_id,
            "blendex_owned": bool(modifier_owned and (tree is None or tree_owned)),
            "ownership": {"modifier": modifier_owned, "node_group": tree_owned},
        }

    def _create_modifier(self, request: OperationRequest) -> Dict[str, Any]:
        object_id = request.target["object_id"]
        obj = self._object(object_id)
        modifier_id = request.params.get("modifier_id", "BlendeX Geometry")
        modifier = self._collection_get(obj.modifiers, modifier_id)
        if modifier is None:
            new_modifier = getattr(obj.modifiers, "new", None)
            if callable(new_modifier):
                try:
                    modifier = new_modifier(name=modifier_id, type="NODES")
                except TypeError:
                    modifier = new_modifier(modifier_id, "NODES")
            elif isinstance(obj.modifiers, dict):
                modifier = {"name": modifier_id, "type": "NODES", "node_group": {"name": f"{modifier_id} Node Tree"}}
                obj.modifiers[modifier_id] = modifier
            else:
                raise BlendexError(
                    "MODIFIER_NOT_FOUND",
                    f"Could not create modifier collection entry: {modifier_id}",
                )
        if self._modifier_type(modifier) != "NODES":
            raise BlendexError("MODIFIER_NOT_FOUND", f"Modifier is not a Geometry Nodes modifier: {modifier_id}")
        tree = self._node_tree(modifier)
        self._set_blendex_owned(modifier)
        self._set_blendex_owned(tree)
        return self._modifier_summary(object_id, modifier, tree)

    def _mark_ownership(self, request: OperationRequest) -> Dict[str, Any]:
        object_id = request.target["object_id"]
        obj = self._object(object_id)
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        tree = self._node_tree(modifier)
        self._set_blendex_owned(modifier)
        self._set_blendex_owned(tree)
        return self._modifier_summary(object_id, modifier, tree)

    def _create_node(self, request: OperationRequest) -> Dict[str, Any]:
        node_type = request.params["node_type"]
        if node_type not in self.context.node_types:
            raise BlendexError(
                "NODE_TYPE_NOT_FOUND",
                f"Node type is unavailable: {node_type}",
                retry_hint="Refresh capabilities and choose a node type reported by Blender.",
            )
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(
            obj,
            request.target.get("modifier_id", "BlendeX Geometry"),
            require_ownership=True,
        )
        tree = self._node_tree(modifier)
        label = request.params.get("label", node_type)
        location = request.params.get("location", [0, 0])
        if hasattr(tree.nodes, "new"):
            node = tree.nodes.new(type=node_type)
            node.label = label
            node.location = location
            summary = self._inspect_node(node)
            summary["node_type"] = node_type
            summary["label"] = label
            summary["location"] = list(location)
            return summary
        node_id = f"node_{len(tree.nodes) + 1}"
        node_data = {"id": node_id, "node_type": node_type, "label": label, "location": list(location)}
        tree.nodes[node_id] = node_data
        return node_data

    def _inspect_tree(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(obj, request.target.get("modifier_id", "BlendeX Geometry"))
        tree = self._existing_node_tree(modifier)
        result = self._modifier_summary(request.target["object_id"], modifier, tree)
        result["nodes"] = [self._inspect_node(node) for node in self._iter_nodes(tree)]
        result["links"] = [self._inspect_link(link) for link in getattr(tree, "links", [])]
        return result

    def _inspect_link(self, link: Any) -> Dict[str, Any]:
        if isinstance(link, dict):
            return link
        summary = {
            "from_node": getattr(getattr(link, "from_node", None), "name", None),
            "from_socket": getattr(getattr(link, "from_socket", None), "name", None),
            "to_node": getattr(getattr(link, "to_node", None), "name", None),
            "to_socket": getattr(getattr(link, "to_socket", None), "name", None),
        }
        socket_type = self._socket_type(getattr(link, "from_socket", None))
        if socket_type:
            summary["socket_type"] = socket_type
        return summary

    def _link_to_socket(self, link: Any) -> Any:
        if isinstance(link, dict):
            return link.get("to_socket")
        return getattr(link, "to_socket", None)

    def _link_to_node(self, link: Any) -> Any:
        if isinstance(link, dict):
            return link.get("to_node")
        return getattr(link, "to_node", None)

    def _node_matches(self, node: Any, reference: Any) -> bool:
        if node is reference:
            return True
        if isinstance(node, str):
            node_id = node
        else:
            node_id = self._node_id(node)
        if isinstance(reference, str):
            reference_id = reference
        else:
            reference_id = self._node_id(reference)
        return bool(node_id) and node_id == reference_id

    def _socket_matches(self, socket: Any, reference: Any) -> bool:
        if socket is reference:
            return True
        if isinstance(socket, str):
            socket_name = socket
        else:
            socket_name = self._socket_name(socket)
        if isinstance(reference, str):
            reference_name = reference
        else:
            reference_name = self._socket_name(reference)
        return bool(socket_name) and socket_name == reference_name

    def _socket_allows_multiple_links(self, socket: Any) -> bool:
        if isinstance(socket, dict):
            return bool(socket.get("is_multi_input") or socket.get("multi_input"))
        return bool(getattr(socket, "is_multi_input", False) or getattr(socket, "multi_input", False))

    def _input_has_link(self, tree: Any, node: Any, socket: Any) -> bool:
        if self._socket_allows_multiple_links(socket):
            return False
        for link in getattr(tree, "links", []) or []:
            if self._node_matches(self._link_to_node(link), node) and self._socket_matches(
                self._link_to_socket(link),
                socket,
            ):
                return True
        return False

    def _value_matches_socket(self, socket: Any, value: Any) -> bool:
        current = None
        has_current = False
        if isinstance(socket, dict):
            if "default_value" in socket:
                current = socket["default_value"]
                has_current = True
        else:
            try:
                current = getattr(socket, "default_value")
                has_current = True
            except Exception:
                has_current = False

        socket_type = self._socket_type(socket)
        if has_current:
            if isinstance(current, bool):
                return isinstance(value, bool)
            if isinstance(current, int) and not isinstance(current, bool):
                return isinstance(value, int) and not isinstance(value, bool)
            if isinstance(current, float):
                return isinstance(value, (int, float)) and not isinstance(value, bool)
            if isinstance(current, str):
                return isinstance(value, str)
            if isinstance(current, (list, tuple)):
                return (
                    isinstance(value, list)
                    and len(value) == len(current)
                    and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
                )

        if "Float" in socket_type:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if "Int" in socket_type:
            return isinstance(value, int) and not isinstance(value, bool)
        if "Bool" in socket_type or "Boolean" in socket_type:
            return isinstance(value, bool)
        if "String" in socket_type:
            return isinstance(value, str)
        if "Vector" in socket_type or "Color" in socket_type:
            return isinstance(value, list) and all(
                isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
            )
        return True

    def _set_socket_default(self, socket: Any, value: Any) -> None:
        if isinstance(socket, dict):
            socket["default_value"] = value
            return
        try:
            setattr(socket, "default_value", value)
        except Exception as exc:
            raise BlendexError(
                "VALUE_TYPE_MISMATCH",
                f"Could not set socket default value: {self._socket_name(socket)}",
                details={"exception": str(exc), "socket_type": self._socket_type(socket)},
            )

    def _set_socket_value(self, request: OperationRequest) -> Dict[str, Any]:
        node, socket = self._validate_set_socket_value(request)
        value = request.params["value"]
        self._set_socket_default(socket, value)
        return {
            "node_id": self._node_id(node),
            "socket": self._socket_name(socket),
            "socket_type": self._socket_type(socket),
            "value": value,
        }

    def _validate_set_socket_value(self, request: OperationRequest) -> tuple[Any, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(
            obj,
            request.target.get("modifier_id", "BlendeX Geometry"),
            require_ownership=True,
        )
        tree = self._existing_node_tree(modifier)
        node = self._node(tree, request.params["node_id"])
        socket = self._socket(node, request.params["socket"], "inputs")
        value = request.params["value"]
        if not self._value_matches_socket(socket, value):
            raise BlendexError(
                "VALUE_TYPE_MISMATCH",
                f"Value is incompatible with socket: {request.params['socket']}",
                details={"socket_type": self._socket_type(socket), "value_type": type(value).__name__},
            )
        return node, socket

    def _link_sockets(self, request: OperationRequest) -> Dict[str, Any]:
        from_node, from_socket, to_node, to_socket, from_type = self._validate_link_sockets(request)
        tree = self._existing_node_tree(
            self._modifier(
                self._object(request.target["object_id"]),
                request.target.get("modifier_id", "BlendeX Geometry"),
                require_ownership=True,
            )
        )
        links = getattr(tree, "links", None)
        new_link = getattr(links, "new", None)
        if callable(new_link):
            link = new_link(from_socket, to_socket)
            summary = self._inspect_link(link)
        else:
            summary = {
                "from_node": self._node_id(from_node),
                "from_socket": self._socket_name(from_socket),
                "to_node": self._node_id(to_node),
                "to_socket": self._socket_name(to_socket),
                "socket_type": from_type,
            }
            if links is not None:
                links.append(summary)
        summary.setdefault("from_node", self._node_id(from_node))
        summary.setdefault("from_socket", self._socket_name(from_socket))
        summary.setdefault("to_node", self._node_id(to_node))
        summary.setdefault("to_socket", self._socket_name(to_socket))
        summary.setdefault("socket_type", from_type)
        return summary

    def _validate_link_sockets(self, request: OperationRequest) -> tuple[Any, Any, Any, Any, str]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(
            obj,
            request.target.get("modifier_id", "BlendeX Geometry"),
            require_ownership=True,
        )
        tree = self._existing_node_tree(modifier)
        from_node = self._node(tree, request.params["from_node"])
        from_socket = self._socket(from_node, request.params["from_socket"], "outputs")
        to_node = self._node(tree, request.params["to_node"])
        to_socket = self._socket(to_node, request.params["to_socket"], "inputs")
        from_type = self._socket_type(from_socket)
        to_type = self._socket_type(to_socket)
        if from_type != to_type:
            raise BlendexError(
                "SOCKET_TYPE_MISMATCH",
                "Cannot link sockets with different types.",
                details={"from_socket_type": from_type, "to_socket_type": to_type},
            )
        if self._input_has_link(tree, to_node, to_socket):
            raise BlendexError(
                "LINK_NOT_ALLOWED",
                "Destination input socket already has a link.",
                details={"to_node": self._node_id(to_node), "to_socket": self._socket_name(to_socket)},
            )
        return from_node, from_socket, to_node, to_socket, from_type

    def _label_node(self, request: OperationRequest) -> Dict[str, Any]:
        obj = self._object(request.target["object_id"])
        modifier = self._modifier(
            obj,
            request.target.get("modifier_id", "BlendeX Geometry"),
            require_ownership=True,
        )
        tree = self._existing_node_tree(modifier)
        node = self._node(tree, request.params["node_id"])
        label = request.params["label"]
        if isinstance(node, dict):
            node["label"] = label
        else:
            node.label = label
        return {"node_id": self._node_id(node), "label": label}

    def _existing_node_tree(self, modifier: Any) -> Any:
        tree = self._raw_node_tree(modifier)
        if tree is None:
            raise BlendexError(
                "NODE_TREE_NOT_FOUND",
                f"Modifier has no Geometry Nodes tree: {self._modifier_name(modifier)}",
            )
        return tree

    def _raw_node_tree(self, modifier: Any) -> Any:
        return modifier.get("node_group") if isinstance(modifier, dict) else getattr(modifier, "node_group", None)

    def _node_tree(self, modifier: Any) -> Any:
        tree = self._raw_node_tree(modifier)
        if tree is not None:
            return tree
        try:
            import bpy

            tree = bpy.data.node_groups.new(f"{self._modifier_name(modifier)} Node Tree", "GeometryNodeTree")
            if isinstance(modifier, dict):
                modifier["node_group"] = tree
            else:
                modifier.node_group = tree
            self._set_blendex_owned(modifier)
            self._set_blendex_owned(tree)
            return tree
        except Exception as exc:
            raise BlendexError(
                "NODE_TREE_NOT_FOUND",
                f"Could not create or access Geometry Nodes tree for modifier: {getattr(modifier, 'name', '')}",
                details={"exception": str(exc)},
            )
