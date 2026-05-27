from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceRecipe:
    recipe_id: int
    title: str
    why_matched: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    missing_ingredients: list[str] = field(default_factory=list)
    time_minutes: int | None = None
    difficulty: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "title": self.title,
            "why_matched": self.why_matched,
            "risk_flags": self.risk_flags,
            "missing_ingredients": self.missing_ingredients,
            "time_minutes": self.time_minutes,
            "difficulty": self.difficulty,
        }


@dataclass(frozen=True)
class EvidencePack:
    recipes: list[EvidenceRecipe] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    live_research_evidence: list[dict[str, Any]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.recipes
            or self.constraints
            or self.live_research_evidence
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "recipes": [recipe.to_payload() for recipe in self.recipes],
            "constraints": self.constraints,
        }

    def to_prompt_context(self) -> str | None:
        if self.is_empty():
            return None
        payload = {
            "recipes": [recipe.to_payload() for recipe in self.recipes],
            "constraints": self.constraints,
            "live_research_evidence": self.live_research_evidence,
        }
        return f"[Evidence pack]\n{payload}"
