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


def _match_recipe(prompt: str) -> Optional[str]:
    normalized = prompt.lower()
    for recipe_id, keywords in _RECIPE_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return recipe_id
    return None


def plan_goal(prompt: str, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    recipe_id = _match_recipe(prompt)
    if recipe_id is not None:
        recipe = REGISTRY.get(recipe_id)
        return {
            "mode": "recipe",
            "recipe_id": recipe_id,
            "label": recipe.label,
            "operations": recipe.build({}),
            "message": f"Matched recipe: {recipe.label}",
        }
    return {
        "mode": "unsupported",
        "error": {
            "code": "PLANNER_UNSUPPORTED_REQUEST",
            "message": "BlendeX v0.3 can plan architecture, hard-surface, nature, and scattering workflows.",
            "retry_hint": (
                "Ask for a modular building, wall panel, grid tower, stone scatter, "
                "grass scatter, or ground point distribution."
            ),
        },
    }
