import hashlib
from dataclasses import dataclass, field

from app.core.config import EMBEDDING_MODEL
from app.models.recipe import RecipeEmbedding
from app.services.embedding_service import EmbeddingService, embedding_service


@dataclass(frozen=True)
class RecipeSearchEmbeddingIngredient:
    name: str
    normalized_name: str | None = None
    amount_text: str | None = None


@dataclass(frozen=True)
class RecipeSearchEmbeddingInput:
    title: str
    summary: str | None = None
    description: str | None = None
    ingredients: list[RecipeSearchEmbeddingIngredient] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    cooking_time_minutes: int | None = None
    difficulty: str | None = None
    kcal_per_serving: int | None = None


class RecipeEmbeddingService:
    def __init__(
        self,
        embedder: EmbeddingService = embedding_service,
        model: str = EMBEDDING_MODEL,
    ):
        self.embedder = embedder
        self.model = model

    def create_search_embedding(
        self,
        recipe_id: int,
        data: RecipeSearchEmbeddingInput,
    ) -> RecipeEmbedding:
        text = build_recipe_search_embedding_text(data)
        return RecipeEmbedding(
            recipe_id=recipe_id,
            embedding_type="RECIPE_SEARCH",
            model=self.model,
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
            embedding=self.embedder.embed_query(text),
        )


def build_recipe_search_embedding_text(data: RecipeSearchEmbeddingInput) -> str:
    sections: list[str] = []
    _append_section(sections, "제목", [data.title])
    _append_section(sections, "요약", [data.summary])
    _append_section(sections, "설명", [data.description])
    _append_section(
        sections,
        "재료",
        [_ingredient_text(item) for item in data.ingredients],
    )
    _append_section(sections, "카테고리", data.categories)
    _append_section(sections, "팁", data.tips)
    _append_section(
        sections,
        "조건",
        [
            f"{data.cooking_time_minutes}분" if data.cooking_time_minutes else None,
            data.difficulty,
            f"{data.kcal_per_serving}kcal" if data.kcal_per_serving else None,
        ],
    )
    return "\n".join(sections)


def _append_section(
    sections: list[str],
    label: str,
    values: list[object],
) -> None:
    texts = [_clean_text(value) for value in values]
    texts = [text for text in texts if text]
    if texts:
        sections.append(f"{label}: {' / '.join(texts)}")


def _ingredient_text(item: RecipeSearchEmbeddingIngredient) -> str:
    parts = [item.normalized_name or item.name, item.amount_text]
    return " ".join(text for text in (_clean_text(part) for part in parts) if text)


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


recipe_embedding_service = RecipeEmbeddingService()
