from pydantic import BaseModel


class IngredientItem(BaseModel):
    name: str
    amount: str
    unit: str
    type: str
    note: str | None = ""


class RecipeSchema(BaseModel):
    title: str
    description: str | None = None
    ingredients_raw: str | None = None
    ingredients: list[IngredientItem] = []
    instructions: list[str] = []
    video_url: str | None = None
    source: str = "STANDARD"
    status: str = "APPROVED"

    class Config:
        from_attributes = True
