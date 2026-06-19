import re
from typing import Any, Dict, Optional

from .recipes import REGISTRY


_RECIPE_KEYWORDS = [
    ("architecture.grid_tower", ("grid tower", "tower", "lattice tower", "modular tower")),
    ("architecture.wall_panel", ("wall", "panel", "facade")),
    ("architecture.modular_building", ("building", "modular building", "blockout")),
    ("scatter.stones", ("stone", "stones", "rock", "rocks")),
    ("scatter.ground_points", ("ground points", "point distribution", "points on ground")),
    ("scatter.grass", ("grass", "field", "lawn")),
]

_CATEGORY_HINTS = {
    "scatter.": ("scatter", "scattering", "distribute", "distribution"),
}


def _has_keyword(prompt: str, keyword: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(keyword).replace(r"\ ", r"\s+") + r"(?!\w)"
    return re.search(pattern, prompt) is not None


def _category_bonus(prompt: str, recipe_id: str) -> int:
    for prefix, hints in _CATEGORY_HINTS.items():
        if recipe_id.startswith(prefix) and any(_has_keyword(prompt, hint) for hint in hints):
            return 2
    return 0


def _match_recipe(prompt: str) -> Optional[str]:
    normalized = prompt.lower()
    best_recipe_id = None
    best_score = 0
    for recipe_id, keywords in _RECIPE_KEYWORDS:
        score = sum(len(keyword.split()) for keyword in keywords if _has_keyword(normalized, keyword))
        if score:
            score += _category_bonus(normalized, recipe_id)
        if score > best_score:
            best_recipe_id = recipe_id
            best_score = score
    return best_recipe_id


def _extract_numeric_value(prompt: str, names: tuple[str, ...], *, value_type: str) -> Any:
    number_pattern = r"\d+(?:\.\d+)?"
    for name in names:
        label_pattern = re.escape(name).replace(r"\ ", r"\s+")
        patterns = (
            rf"(?<!\w){label_pattern}s?\s*(?P<value>{number_pattern})(?!\w)",
            rf"(?<!\w)(?P<value>{number_pattern})\s*(?:-| )?\s*{label_pattern}s?(?!\w)",
        )
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                raw_value = match.group("value")
                return int(raw_value) if value_type == "integer" else float(raw_value)
    return None


def _extract_parameters(prompt: str, recipe: Any) -> Dict[str, Any]:
    aliases = {
        "levels": ("level", "levels", "floor", "floors", "story", "stories"),
        "columns": ("column", "columns", "bay", "bays"),
        "segments": ("segment", "segments"),
        "floors": ("floor", "floors", "story", "stories", "level", "levels"),
        "density": ("density",),
        "seed": ("seed",),
        "scale": ("scale",),
    }
    extracted: Dict[str, Any] = {}
    for parameter in recipe.parameters:
        names = aliases.get(parameter.name, (parameter.name,))
        value = _extract_numeric_value(prompt, names, value_type=parameter.value_type)
        if value is not None:
            extracted[parameter.name] = value
    return extracted


def _missing_node_types(recipe: Any, capabilities: Optional[Dict[str, Any]]) -> list[str]:
    if not isinstance(capabilities, dict):
        return []
    node_types = capabilities.get("node_types")
    if not isinstance(node_types, dict) or not node_types:
        return []
    available = set(node_types)
    return [node_type for node_type in recipe.required_node_types if node_type not in available]


def _unsupported(message: str, retry_hint: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    error = {
        "code": "PLANNER_UNSUPPORTED_REQUEST",
        "message": message,
        "retry_hint": retry_hint,
    }
    if details is not None:
        error["details"] = details
    return {"mode": "unsupported", "error": error}


def plan_goal(prompt: str, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    recipe_id = _match_recipe(prompt)
    if recipe_id is not None:
        recipe = REGISTRY.get(recipe_id)
        missing_node_types = _missing_node_types(recipe, capabilities)
        if missing_node_types:
            return _unsupported(
                f"BlendeX cannot run {recipe.label}; missing node types: {', '.join(missing_node_types)}.",
                "Refresh Blender capabilities or choose another supported BlendeX recipe.",
                {"missing_node_types": missing_node_types},
            )
        parameters = _extract_parameters(prompt.lower(), recipe)
        try:
            operations = recipe.build(parameters)
        except ValueError as error:
            return _unsupported(
                f"BlendeX cannot run {recipe.label}: {error}.",
                "Use recipe parameters within the supported ranges.",
                {"recipe_id": recipe_id, "parameters": parameters},
            )
        return {
            "mode": "recipe",
            "recipe_id": recipe_id,
            "label": recipe.label,
            "parameters": parameters,
            "operations": operations,
            "message": f"Matched recipe: {recipe.label}",
        }
    return _unsupported(
        "BlendeX v0.4 can plan architecture, hard-surface, nature, and scattering workflows.",
        (
            "Ask for a modular building, wall panel, grid tower, stone scatter, "
            "grass scatter, or ground point distribution."
        ),
    )
