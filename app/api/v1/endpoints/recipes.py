# 레시피 CRUD 및 추천 목록 조회
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_recipes():
    return {"message": "Recipes endpoint"}
