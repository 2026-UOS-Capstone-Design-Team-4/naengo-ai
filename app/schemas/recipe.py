from typing import Literal

from pydantic import BaseModel


class IngredientItem(BaseModel):
    name: str
    amount: str
    unit: str
    type: str
    note: str | None = ""


class RecipeBase(BaseModel):
    title: str
    description: str
    ingredients: list[IngredientItem] = []
    ingredients_raw: str
    instructions: list[str] = []
    servings: float
    cooking_time: int
    calories: int | None = None
    difficulty: Literal["easy", "normal", "hard"]
    category: list[str] = []
    tags: list[str] = []
    tips: list[str] = []
    video_url: str | None = None
    image_url: str | None = None

    class Config:
        from_attributes = True


class RecipeSchema(RecipeBase):
    content: str | None = None
    author_type: Literal["ADMIN", "USER"] = "ADMIN"


class RecipeResponse(RecipeBase):
    """recipes SSE 이벤트로 전달되는 레시피 데이터"""
    id: int
    author_type: Literal["ADMIN", "USER"]
