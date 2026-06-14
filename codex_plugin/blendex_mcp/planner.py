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
    "architecture.": ("build", "building", "modular", "facade", "panel", "tower"),
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
