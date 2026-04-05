# Pydantic 모델 (API Req/Res 및 AI 결과 형식)
from pydantic import BaseModel


class RecipeSchema(BaseModel):
    name: str
