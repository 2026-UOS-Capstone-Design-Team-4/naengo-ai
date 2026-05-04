from fastapi import APIRouter

from app.api.v1.admin import recipes as admin_recipes
from app.api.v1.endpoints import chat, pending_recipes, recipes, users

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(pending_recipes.router, prefix="/pending-recipes", tags=["pending-recipes"])
api_router.include_router(admin_recipes.router, prefix="/admin/recipes", tags=["admin"])
