from types import SimpleNamespace

from app.agents.core.memory import AgentMemory, LongTermMemory
from app.services.retrieval_orchestrator import RetrievalOrchestrator


class FakeRetrievalService:
    def search_recipes(self, query, limit=3, plan=None):
        return [
            SimpleNamespace(recipe_id=1, title="두부 김치찌개"),
            SimpleNamespace(recipe_id=2, title="새우 볶음밥"),
        ]

    def recipe_to_payload(self, recipe, liked_ids=None, scrapped_ids=None):
        if recipe.recipe_id == 1:
            return {
                "id": 1,
                "title": recipe.title,
                "description": "김치와 두부로 끓이는 찌개",
                "ingredients": [{"name": "김치"}, {"name": "두부"}],
                "cooking_time_minutes": 20,
                "difficulty": "easy",
            }
        return {
            "id": 2,
            "title": recipe.title,
            "description": "새우로 만드는 볶음밥",
            "ingredients": [{"name": "새우"}, {"name": "밥"}],
            "cooking_time_minutes": 15,
            "difficulty": "easy",
        }


def test_search_builds_evidence_pack_and_filters_allergies():
    plan = SimpleNamespace(
        main_ingredients=["김치", "두부"],
        available_ingredients=["김치", "두부"],
        preferred_ingredients=[],
        required_ingredients=[],
        avoid_ingredients=[],
        allergies=["새우"],
        target_dish_name=None,
        cooking_time_max=20,
    )
    memory = AgentMemory(long_term=LongTermMemory(allergies=["새우"]))

    result = RetrievalOrchestrator(FakeRetrievalService()).search(
        "김치 두부 찌개",
        plan=plan,
        memory=memory,
    )

    assert [payload["id"] for payload in result.recipe_payloads] == [1]
    assert result.evidence_pack.constraints["avoid_ingredients"] == ["새우"]
    evidence = result.evidence_pack.recipes[0]
    assert evidence.recipe_id == 1
    assert evidence.why_matched == ["김치", "두부", "20분 이내"]
    assert evidence.risk_flags == []
