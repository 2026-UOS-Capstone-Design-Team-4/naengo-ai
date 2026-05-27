from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ShortTermMemory:
    recent_recipe_ids: list[int] = field(default_factory=list)
    recent_ingredients: list[str] = field(default_factory=list)
    current_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LongTermMemory:
    allergies: list[str] = field(default_factory=list)
    dietary_restrictions: list[str] = field(default_factory=list)
    preferred_ingredients: list[str] = field(default_factory=list)
    disliked_ingredients: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    taste_keywords: list[str] = field(default_factory=list)
    cooking_skill: str | None = None
    preferred_cooking_time_minutes: int | None = None
    serving_size: float | None = None


@dataclass(frozen=True)
class AgentMemory:
    short_term: ShortTermMemory = field(default_factory=ShortTermMemory)
    long_term: LongTermMemory | None = None

    def to_prompt_context(self) -> str | None:
        lines: list[str] = []
        short = self.short_term
        if short.recent_recipe_ids:
            ids = ", ".join(str(recipe_id) for recipe_id in short.recent_recipe_ids)
            lines.append(f"- recent_recipe_ids: {ids}")
        if short.recent_ingredients:
            lines.append(f"- recent_ingredients: {', '.join(short.recent_ingredients)}")
        if short.current_constraints:
            lines.append(f"- current_constraints: {short.current_constraints}")

        long = self.long_term
        if long is not None:
            if long.allergies:
                lines.append(f"- allergies: {', '.join(long.allergies)}")
            if long.dietary_restrictions:
                lines.append(
                    "- dietary_restrictions: "
                    f"{', '.join(long.dietary_restrictions)}"
                )
            if long.preferred_ingredients:
                lines.append(
                    "- preferred_ingredients: "
                    f"{', '.join(long.preferred_ingredients)}"
                )
            if long.disliked_ingredients:
                lines.append(
                    "- disliked_ingredients: "
                    f"{', '.join(long.disliked_ingredients)}"
                )
            if long.preferred_categories:
                lines.append(
                    "- preferred_categories: "
                    f"{', '.join(long.preferred_categories)}"
                )
            if long.taste_keywords:
                lines.append(f"- taste_keywords: {', '.join(long.taste_keywords)}")
            if long.cooking_skill:
                lines.append(f"- cooking_skill: {long.cooking_skill}")
            if long.preferred_cooking_time_minutes:
                lines.append(
                    "- preferred_cooking_time_minutes: "
                    f"{long.preferred_cooking_time_minutes}"
                )
            if long.serving_size:
                lines.append(f"- serving_size: {long.serving_size:g}")

        if not lines:
            return None
        return "[Agent memory]\n" + "\n".join(lines)

