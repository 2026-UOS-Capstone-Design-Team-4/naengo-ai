# Agent가 사용할 RunContext(DB, User context) 정의
from dataclasses import dataclass, field


@dataclass
class RecipeDeps:
    last_found_recipes: list[dict] = field(default_factory=list)
