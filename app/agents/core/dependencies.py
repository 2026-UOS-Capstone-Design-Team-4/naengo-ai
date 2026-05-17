from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.recipe.search_planner import SearchPlan


@dataclass
class RecipeDeps:
    last_found_recipes: list[dict] = field(default_factory=list)
    search_plan: SearchPlan | None = None

