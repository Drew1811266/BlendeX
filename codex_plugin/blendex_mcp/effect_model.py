import re
from typing import Any, Dict, Iterable, List


_EFFECT_KEYWORDS = {
    "architecture": (
        "architecture",
        "building",
        "tower",
        "facade",
        "floor",
        "floors",
        "wall",
        "panel",
        "roof",
        "bridge",
        "pavilion",
        "balcony",
        "balconies",
        "column",
        "columns",
    ),
    "scatter": (
        "scatter",
        "distribute",
        "density",
        "grass",
        "rocks",
        "rock",
        "pebbles",
        "pebble",
        "trees",
        "tree",
        "points on",
    ),
    "instance": (
        "instance",
        "instances",
        "instancing",
        "repeating",
        "repeated",
        "modules",
        "module",
        "every other",
        "place",
        "around a circle",
    ),
    "deform": (
        "deform",
        "deforming",
        "ripple",
        "wave",
        "offset",
        "terrain",
        "noise",
        "taper",
        "tapered",
        "smaller near",
        "extrude",
        "bevel",
        "upward",
        "height offsets",
    ),
    "field": (
        "field",
        "random",
        "noise",
        "sinusoidal",
        "height",
        "slope",
        "index",
        "checker",
        "checkerboard",
        "center",
        "edges",
        "gradient",
        "density",
        "based on",
    ),
    "attribute": (
        "attribute",
        "attributes",
        "capture",
        "store",
        "named",
        "vertex group",
        "density attribute",
        "floor index",
        "original position",
    ),
    "material": (
        "material",
        "materials",
        "color",
        "colour",
        "shading",
        "warm",
        "cool",
        "trim",
        "darker",
        "assign",
    ),
    "selection": (
        "select",
        "selection",
        "mask",
        "every other",
        "checker",
        "checkerboard",
        "upper",
        "steep",
        "boundary",
        "only where",
        "alternating",
    ),
    "simulation": (
        "simulation",
        "simulate",
        "fluid",
        "physics",
        "cloth",
        "frames",
    ),
    "character": (
        "character",
        "skin",
        "hair",
        "photoreal",
        "cinematic character",
    ),
}

_PRIMARY_PRIORITY = (
    "material",
    "attribute",
    "scatter",
    "architecture",
    "deform",
    "instance",
    "selection",
    "field",
)

_PARAMETER_ALIASES = {
    "floors": ("floor", "floors", "story", "stories", "level", "levels"),
    "columns": ("column", "columns", "bay", "bays"),
    "density": ("density",),
    "seed": ("seed",),
    "count": ("count",),
}


def _contains_any(prompt: str, keywords: Iterable[str]) -> bool:
    return any(keyword in prompt for keyword in keywords)


def _append_unique(values: List[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _extract_numeric_value(prompt: str, aliases: Iterable[str]) -> Any:
    number_pattern = r"\d+(?:\.\d+)?"
    for alias in aliases:
        escaped = re.escape(alias).replace(r"\ ", r"\s+")
        patterns = (
            rf"(?<!\w)(?P<value>{number_pattern})\s*(?:-| )?\s*{escaped}s?(?!\w)",
            rf"(?<!\w){escaped}s?\s*(?P<value>{number_pattern})(?!\w)",
        )
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if not match:
                continue
            raw_value = match.group("value")
            number = float(raw_value)
            return int(number) if number.is_integer() else number
    return None


def _extract_parameters(prompt: str) -> Dict[str, Any]:
    parameters: Dict[str, Any] = {}
    for name, aliases in _PARAMETER_ALIASES.items():
        value = _extract_numeric_value(prompt, aliases)
        if value is not None:
            parameters[name] = value
    return parameters


def _constraints_for_prompt(prompt: str) -> List[str]:
    constraints: List[str] = []
    if _contains_any(prompt, ("repeating", "repeated", "every other", "alternating")):
        _append_unique(constraints, "repetition")
    if _contains_any(prompt, ("smaller near", "taper", "random scale", "height offsets")):
        _append_unique(constraints, "scale variation")
    if _contains_any(prompt, ("center", "edges", "sparsely", "densely")):
        _append_unique(constraints, "density gradient")
    if _contains_any(prompt, ("height", "upper", "top")):
        _append_unique(constraints, "height based")
    if _contains_any(prompt, ("slope", "steep", "normal")):
        _append_unique(constraints, "slope based")
    if _contains_any(prompt, ("capture", "original position", "before deform")):
        _append_unique(constraints, "capture before deformation")
    if _contains_any(prompt, ("exposed parameter", "parameter", "controllable")):
        _append_unique(constraints, "exposed parameter")
    if _contains_any(prompt, ("checker", "checkerboard", "every other", "alternating")):
        _append_unique(constraints, "index pattern")
    if _contains_any(prompt, ("random", "noise")):
        _append_unique(constraints, "random variation")
    return constraints


def _effects_for_prompt(prompt: str) -> List[str]:
    effects: List[str] = []
    for effect, keywords in _EFFECT_KEYWORDS.items():
        if _contains_any(prompt, keywords):
            effects.append(effect)
    if "attribute" in effects and _contains_any(prompt, ("capture", "original position")):
        _append_unique(effects, "field")
    if "scatter" in effects and _contains_any(prompt, ("density", "densely", "sparsely", "center", "edges")):
        _append_unique(effects, "selection")
    return effects


def _unsupported_reasons(prompt: str, effects: Iterable[str]) -> List[str]:
    reasons: List[str] = []
    if "simulation" in effects:
        reasons.append("simulation_zones_out_of_scope")
    if "character" in effects and _contains_any(prompt, ("photoreal", "cinematic", "hair", "skin")):
        reasons.append("photoreal_character_out_of_scope")
    return reasons


def _primary_effect(effects: List[str], unsupported_reasons: List[str]) -> str:
    if unsupported_reasons:
        return "unsupported"
    for effect in _PRIMARY_PRIORITY:
        if effect in effects:
            return effect
    return "unknown"


def parse_effect_intent(prompt: str) -> Dict[str, Any]:
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be a string")
    normalized = " ".join(prompt.lower().split())
    effects = _effects_for_prompt(normalized)
    unsupported_reasons = _unsupported_reasons(normalized, effects)
    primary_effect = _primary_effect(effects, unsupported_reasons)
    constraints = _constraints_for_prompt(normalized)
    parameters = _extract_parameters(normalized)
    explanation = (
        f"Parsed {primary_effect} intent with effects: {', '.join(effects) or 'none'}."
    )
    if unsupported_reasons:
        explanation += f" Unsupported reasons: {', '.join(unsupported_reasons)}."
    return {
        "prompt": prompt,
        "normalized_prompt": normalized,
        "primary_effect": primary_effect,
        "effects": effects,
        "parameters": parameters,
        "constraints": constraints,
        "unsupported_reasons": unsupported_reasons,
        "explanation": explanation,
    }
