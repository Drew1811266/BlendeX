import copy
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


RecipeBuilder = Callable[[Dict[str, Any]], List[Dict[str, Any]]]


@dataclass
class RecipeParameter:
    name: str
    value_type: str
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    description: str = ""

    def metadata(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "value_type": self.value_type,
            "default": copy.deepcopy(self.default),
            "description": self.description,
        }
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        return result

    def normalize(self, params: Dict[str, Any]) -> Any:
        value = copy.deepcopy(params.get(self.name, self.default))
        if self.value_type == "integer":
            self._validate_integer(value)
        elif self.value_type == "number":
            self._validate_number(value)
        elif self.value_type == "string":
            self._validate_string(value)
        else:
            raise ValueError(f"Unsupported recipe parameter type for {self.name}: {self.value_type}")
        return value

    def _validate_integer(self, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Recipe parameter {self.name} must be an integer")
        self._validate_range(value)

    def _validate_number(self, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Recipe parameter {self.name} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"Recipe parameter {self.name} must be finite")
        self._validate_range(value)

    def _validate_string(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValueError(f"Recipe parameter {self.name} must be a string")
        if not value.strip():
            raise ValueError(f"Recipe parameter {self.name} must be a non-empty string")

    def _validate_range(self, value: Any) -> None:
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"Recipe parameter {self.name} must be >= {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"Recipe parameter {self.name} must be <= {self.maximum}")


@dataclass
class Recipe:
    recipe_id: str
    label: str
    category: str
    parameters: List[RecipeParameter]
    builder: RecipeBuilder
    required_node_types: List[str] = field(default_factory=list)
    example_prompts: List[str] = field(default_factory=list)

    def metadata(self) -> Dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "label": self.label,
            "category": self.category,
            "parameters": [parameter.metadata() for parameter in self.parameters],
            "required_node_types": list(self.required_node_types),
            "example_prompts": list(self.example_prompts),
        }

    def normalize_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ValueError("Recipe parameters must be an object")
        known_parameters = {parameter.name for parameter in self.parameters}
        unknown_parameters = sorted(set(params) - known_parameters)
        if unknown_parameters:
            raise ValueError(f"Unknown recipe parameter: {unknown_parameters[0]}")
        return {parameter.name: parameter.normalize(params) for parameter in self.parameters}

    def build(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.builder(self.normalize_params(params))


class RecipeRegistry:
    def __init__(self) -> None:
        self._recipes: Dict[str, Recipe] = {}

    def register(self, recipe: Recipe) -> None:
        if not isinstance(recipe.recipe_id, str) or not recipe.recipe_id.strip():
            raise ValueError("Recipe id must be a non-empty string")
        if recipe.recipe_id in self._recipes:
            raise ValueError(f"Duplicate recipe id: {recipe.recipe_id}")
        self._recipes[recipe.recipe_id] = recipe

    def get(self, recipe_id: str) -> Recipe:
        try:
            return self._recipes[recipe_id]
        except KeyError as error:
            raise ValueError(f"Unknown recipe: {recipe_id}") from error

    def list_recipes(self) -> List[Dict[str, Any]]:
        return [recipe.metadata() for recipe in self._recipes.values()]

    def build(self, recipe_id: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.get(recipe_id).build(params)


def _carrier(name: str) -> Dict[str, Any]:
    return {
        "id": f"create_{name.lower().replace(' ', '_')}",
        "type": "scene.create_carrier_mesh",
        "target": {},
        "params": {"name": name},
    }


def _modifier(
    object_id: str = "BlendeX Carrier",
    modifier_id: str = "BlendeX Geometry",
) -> Dict[str, Any]:
    return {
        "id": "create_modifier",
        "type": "geometry_nodes.create_modifier",
        "target": {"object_id": object_id},
        "params": {"modifier_id": modifier_id},
    }


def _node(
    op_id: str,
    object_id: str,
    client_id: str,
    node_type: str,
    label: str,
    location: List[float],
) -> Dict[str, Any]:
    return {
        "id": op_id,
        "type": "geometry_nodes.create_node",
        "target": {"object_id": object_id, "modifier_id": "BlendeX Geometry"},
        "params": {
            "node_type": node_type,
            "label": label,
            "client_id": client_id,
            "location": location,
        },
    }


def _grid_tower(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Grid Tower"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node(
            "grid_join",
            object_id,
            "grid_join",
            "GeometryNodeJoinGeometry",
            f"Grid Tower {params['levels']}x{params['columns']}",
            [0, 0],
        ),
        _node(
            "grid_transform",
            object_id,
            "grid_transform",
            "GeometryNodeTransform",
            "Module Transform",
            [220, 0],
        ),
    ]


def _wall_panel(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Wall Panel"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node(
            "wall_join",
            object_id,
            "wall_join",
            "GeometryNodeJoinGeometry",
            f"Wall Panel {params['segments']} segments",
            [0, 0],
        ),
        _node(
            "wall_transform",
            object_id,
            "wall_transform",
            "GeometryNodeTransform",
            "Panel Transform",
            [220, 0],
        ),
    ]


def _modular_building(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    object_id = "BlendeX Modular Building"
    return [
        _carrier(object_id),
        _modifier(object_id),
        _node(
            "building_join",
            object_id,
            "building_join",
            "GeometryNodeJoinGeometry",
            f"Building {params['floors']} floors",
            [0, 0],
        ),
        _node(
            "building_set_material",
            object_id,
            "building_material",
            "GeometryNodeSetMaterial",
            "Material Zones",
            [220, -180],
        ),
    ]


REGISTRY = RecipeRegistry()
REGISTRY.register(
    Recipe(
        recipe_id="architecture.grid_tower",
        label="Modular Grid Tower",
        category="architecture",
        parameters=[
            RecipeParameter("levels", "integer", default=5, minimum=1, maximum=40),
            RecipeParameter("columns", "integer", default=4, minimum=1, maximum=20),
        ],
        builder=_grid_tower,
        required_node_types=["GeometryNodeJoinGeometry", "GeometryNodeTransform"],
        example_prompts=["Create a modular grid tower"],
    )
)
REGISTRY.register(
    Recipe(
        recipe_id="architecture.wall_panel",
        label="Procedural Wall Panel",
        category="architecture",
        parameters=[RecipeParameter("segments", "integer", default=6, minimum=1, maximum=40)],
        builder=_wall_panel,
        required_node_types=["GeometryNodeJoinGeometry", "GeometryNodeTransform"],
        example_prompts=["Create a procedural wall panel"],
    )
)
REGISTRY.register(
    Recipe(
        recipe_id="architecture.modular_building",
        label="Simple Modular Building",
        category="architecture",
        parameters=[RecipeParameter("floors", "integer", default=4, minimum=1, maximum=30)],
        builder=_modular_building,
        required_node_types=["GeometryNodeJoinGeometry", "GeometryNodeSetMaterial"],
        example_prompts=["Create a simple modular building"],
    )
)
