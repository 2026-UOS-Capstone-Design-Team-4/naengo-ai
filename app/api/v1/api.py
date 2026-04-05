from fastapi import APIRouter

from app.api.v1.endpoints import chat, recipes

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
