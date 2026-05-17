from types import SimpleNamespace

from app.services.recipe_embedding_service import (
    RecipeEmbeddingService,
    RecipeSearchEmbeddingIngredient,
    RecipeSearchEmbeddingInput,
    build_recipe_search_embedding_text,
)


def test_build_recipe_search_embedding_text_includes_search_context():
    text = build_recipe_search_embedding_text(
        RecipeSearchEmbeddingInput(
            title="김치 두부찌개",
            summary="김치와 두부로 끓이는 국물 요리",
            description="칼칼한 맛으로 먹기 좋은 찌개입니다.",
            ingredients=[
                RecipeSearchEmbeddingIngredient(
                    name="김치",
                    normalized_name="배추김치",
                    amount_text="200g",
                ),
                RecipeSearchEmbeddingIngredient(name="두부", amount_text="1모"),
            ],
            categories=["한식", "찌개"],
            tips=["김치는 묵은지를 사용하면 좋습니다."],
            cooking_time_minutes=20,
            difficulty="easy",
            kcal_per_serving=180,
        )
    )

    assert "재료:" in text
    assert "재료: 배추김치 200g / 두부 1모" in text
    assert "잘 익은 것" not in text
    assert "카테고리: 한식 / 찌개" in text
    assert "조건: 20분 / easy / 180kcal" in text
    assert "조리법:" not in text
    assert "태그:" not in text


def test_create_search_embedding_uses_built_text_hash_and_vector():
    captured = {}

    def embed_query(text):
        captured["text"] = text
        return [0.1, 0.2, 0.3]

    service = RecipeEmbeddingService(
        embedder=SimpleNamespace(embed_query=embed_query),
        model="test-model",
    )

    embedding = service.create_search_embedding(
        recipe_id=10,
        data=RecipeSearchEmbeddingInput(
            title="버섯 볶음",
            ingredients=[
                RecipeSearchEmbeddingIngredient(name="버섯", amount_text="100g")
            ],
        ),
    )

    assert embedding.recipe_id == 10
    assert embedding.embedding_type == "RECIPE_SEARCH"
    assert embedding.model == "test-model"
    assert embedding.embedding == [0.1, 0.2, 0.3]
    assert "버섯 100g" in captured["text"]
    assert embedding.content_hash != "pending"
