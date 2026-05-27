from types import SimpleNamespace

from app.agents.cooking_qa.planner import CookingQAPlan, ReferencedRecipe
from app.agents.intent.intent_models import AnswerStrategy, CookingQASubIntent
from app.services.agent_context_resolver import AgentContextResolver


class FakeQuery:
    def __init__(self, recipe):
        self.recipe = recipe

    def filter(self, *args):
        return self

    def options(self, *args):
        return self

    def first(self):
        return self.recipe


class FakeDb:
    def __init__(self, recipe):
        self.recipe = recipe

    def query(self, model):
        return FakeQuery(self.recipe)


def test_explicit_title_resolves_recipe_with_structured_prompt_context():
    recipe = SimpleNamespace(
        recipe_id=42,
        title="김치찌개",
        summary="칼칼한 찌개",
        description="김치와 돼지고기를 넣고 끓이는 레시피입니다.",
        servings=2,
        cooking_time_minutes=30,
        difficulty="easy",
        ingredients_list=[
            SimpleNamespace(
                group_name="주재료",
                name="김치",
                amount_text="200g",
                unit=None,
                note="신김치",
                raw_text="김치 200g",
                is_optional=False,
            ),
            SimpleNamespace(
                group_name="주재료",
                name="돼지고기",
                amount_text="100g",
                unit=None,
                note=None,
                raw_text="돼지고기 100g",
                is_optional=False,
            ),
        ],
        steps=[
            SimpleNamespace(
                step_no=1,
                instruction="냄비에 돼지고기와 김치를 볶습니다.",
                tip="김치가 숨이 죽을 때까지 볶으세요.",
            ),
            SimpleNamespace(
                step_no=2,
                instruction="물을 붓고 끓입니다.",
                tip=None,
            ),
        ],
        tips=["마지막에 대파를 넣으면 향이 좋아요."],
        warnings=["돼지고기는 충분히 익히세요."],
        nutrition=SimpleNamespace(
            serving_weight_grams=350,
            kcal_per_serving=420,
            carbohydrate_grams=15,
            protein_grams=22,
            fat_grams=28,
            sodium_milligrams=1100,
        ),
    )
    plan = CookingQAPlan(
        sub_intent=CookingQASubIntent.RECIPE_CONTEXT,
        question_type="RECIPE_REFERENCE",
        referenced_recipe=ReferencedRecipe(
            reference_type="EXPLICIT_TITLE",
            title="김치찌개",
            confidence=0.9,
        ),
        referenced_step_no=1,
        referenced_ingredients=["돼지고기"],
        needs_recipe_context=True,
        rewritten_question="김치찌개에서 돼지고기를 빼도 돼?",
        answer_strategy=AnswerStrategy.RECIPE_CONTEXT_QA,
    )

    resolved = AgentContextResolver().resolve_cooking_qa(
        plan,
        room_id=1,
        chat_service=None,
        db=FakeDb(recipe),
    )

    assert resolved.recipe_ids == [42]
    assert resolved.payload["resolved_recipe_id"] == 42
    assert resolved.payload["title"] == "김치찌개"
    assert resolved.payload["referenced_step_no"] == 1
    assert resolved.payload["referenced_ingredients"] == ["돼지고기"]
    assert resolved.payload["recipe"]["ingredients"][0]["name"] == "김치"
    assert resolved.payload["recipe"]["steps"][0]["instruction"] == (
        "냄비에 돼지고기와 김치를 볶습니다."
    )
    assert resolved.payload["recipe"]["nutrition"]["kcal_per_serving"] == 420
