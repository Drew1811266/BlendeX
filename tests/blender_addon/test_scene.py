import unittest

from blender_addon.blendex.scene import create_carrier_mesh, inspect_scene


class FakeNodeGroup:
    def __init__(self, name):
        self.name = name


class FakeModifier:
    def __init__(self, name, modifier_type="NODES", owned=False, node_group=None):
        self.name = name
        self.type = modifier_type
        self.node_group = node_group
        self._props = {"blendex_owned": owned}

    def get(self, key, default=None):
        return self._props.get(key, default)


class FakeObject:
    def __init__(self, name, object_type="MESH", visible=True):
        self.name = name
        self.type = object_type
        self.modifiers = []
        self.hide_viewport = not visible
        self.selected = False

    def select_get(self):
        return self.selected

    def select_set(self, selected):
        self.selected = selected


class FakeObjectStore(list):
    def get(self, name):
        for obj in self:
            if obj.name == name:
                return obj
        return None


class FakeSceneContext:
    def __init__(self, objects=None, selected_object=None):
        self.objects = FakeObjectStore(objects or [])
        self.selected_objects = []
        self.object = None
        self.version = (4, 2, 1)
        self.created = []
        self.selection_updates = []
        self.active_updates = []
        if selected_object is not None:
            selected_object.selected = True
            self.selected_objects = [selected_object]
            self.object = selected_object

    def create_mesh_object(self, name):
        obj = FakeObject(name)
        self.objects.append(obj)
        self.created.append(obj)
        return obj

    def select_object(self, obj):
        for existing in self.objects:
            existing.selected = False
        obj.selected = True
        self.selected_objects = [obj]
        self.selection_updates.append(obj.name)

    def set_active_object(self, obj):
        self.object = obj
        self.active_updates.append(obj.name)


class SceneInspectionTests(unittest.TestCase):
    def test_inspect_scene_returns_rich_selection_modifier_and_recommendation_context(self):
        cube = FakeObject("Cube")
        cube.modifiers.append(
            FakeModifier(
                "BlendeX Geometry",
                owned=True,
                node_group=FakeNodeGroup("BlendeX Geometry Nodes"),
            )
        )
        cube.modifiers.append(FakeModifier("Bevel", modifier_type="BEVEL"))
        hidden_empty = FakeObject("Guide", object_type="EMPTY", visible=False)
        context = FakeSceneContext([cube, hidden_empty], selected_object=cube)

        result = inspect_scene(context)

        self.assertEqual(result["blender_version"], [4, 2, 1])
        self.assertEqual(result["selected_objects"], ["Cube"])
        self.assertEqual(result["selected_object"], "Cube")
        self.assertEqual(result["objects"][0]["id"], "Cube")
        self.assertTrue(result["objects"][0]["selected"])
        self.assertFalse(result["objects"][1]["visible"])
        blendex_modifier = result["objects"][0]["modifiers"][0]
        self.assertEqual(blendex_modifier["name"], "BlendeX Geometry")
        self.assertEqual(blendex_modifier["node_group"], "BlendeX Geometry Nodes")
        self.assertTrue(blendex_modifier["blendex_owned"])
        self.assertTrue(blendex_modifier["safe_for_mutation"])
        self.assertFalse(result["objects"][0]["modifiers"][1]["safe_for_mutation"])
        self.assertEqual(
            result["recommended_target"],
            {
                "object_id": "Cube",
                "modifier_id": "BlendeX Geometry",
                "reason": "selected_blendex_modifier",
            },
        )

    def test_inspect_scene_recommends_selected_mesh_without_owned_modifier(self):
        plane = FakeObject("Plane")
        context = FakeSceneContext([plane], selected_object=plane)

        result = inspect_scene(context)

        self.assertEqual(
            result["recommended_target"],
            {"object_id": "Plane", "reason": "selected_mesh_without_blendex_modifier"},
        )

    def test_create_carrier_mesh_uses_context_factory_and_updates_selection(self):
        existing = FakeObject("Existing")
        context = FakeSceneContext([existing], selected_object=existing)

        result = create_carrier_mesh(context, "Generated Carrier")

        self.assertEqual(result["object_id"], "Generated Carrier")
        self.assertEqual(result["name"], "Generated Carrier")
        self.assertEqual(result["selected_object"], "Generated Carrier")
        self.assertEqual(context.created[0].name, "Generated Carrier")
        self.assertEqual(context.selection_updates, ["Generated Carrier"])
        self.assertEqual(context.active_updates, ["Generated Carrier"])
        self.assertEqual(context.selected_objects[0].name, "Generated Carrier")
        self.assertEqual(context.object.name, "Generated Carrier")
        self.assertFalse(existing.selected)


if __name__ == "__main__":
    unittest.main()
