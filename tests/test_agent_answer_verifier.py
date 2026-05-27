from types import SimpleNamespace

from app.agents.core.memory import AgentMemory, LongTermMemory, ShortTermMemory
from app.agents.intent.intent_models import AnswerStrategy
from app.services.agent_answer_verifier import AnswerVerifier


def test_answer_verifier_flags_allergy_recipe():
    memory = AgentMemory(long_term=LongTermMemory(allergies=["새우"]))
    recipes = [{"id": 1, "title": "새우 볶음밥", "ingredients": [{"name": "새우"}]}]

    result = AnswerVerifier().verify("추천드려요.", recipes, memory)

    assert result.passed is False
    assert result.issues == ["recipe_contains_allergy:새우"]


def test_answer_verifier_passes_when_recipe_avoids_allergy():
    memory = AgentMemory(long_term=LongTermMemory(allergies=["새우"]))
    recipes = [{"id": 1, "title": "두부 볶음", "ingredients": [{"name": "두부"}]}]

    result = AnswerVerifier().verify("새우는 피해서 골랐어요.", recipes, memory)

    assert result.passed is True


def test_answer_verifier_flags_current_avoid_conflict():
    memory = AgentMemory(
        short_term=ShortTermMemory(
            current_constraints={"avoid_ingredients": ["고수"]},
        )
    )
    recipes = [{"id": 1, "title": "고수 샐러드", "ingredients": [{"name": "고수"}]}]

    result = AnswerVerifier().verify("고수는 피해서 골랐어요.", recipes, memory)

    assert result.passed is False
    assert "recipe_contains_avoid_ingredient:고수" in result.issues
    assert "answer_recipe_conflict_avoid_ingredient:고수" in result.issues


def test_answer_verifier_flags_no_recipe_text_with_payload():
    recipes = [{"id": 1, "title": "두부 볶음", "ingredients": [{"name": "두부"}]}]

    result = AnswerVerifier().verify("검색 결과가 없습니다.", recipes, None)

    assert result.passed is False
    assert "answer_payload_mismatch:no_recipes_text_with_payload" in result.issues


def test_answer_verifier_flags_overly_permissive_safety_answer():
    plan = SimpleNamespace(safety_sensitive=True)

    result = AnswerVerifier().verify(
        "먹어도 돼요.",
        [],
        None,
        plan=plan,
        answer_strategy=AnswerStrategy.SAFETY_COOKING_QA,
    )

    assert result.passed is False
    assert "safety_answer_too_permissive" in result.issues
