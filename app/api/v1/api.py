from fastapi import APIRouter, Depends

from app.api.v1.deps import require_admin
from app.api.v1.endpoints import chat, user_recipes, recipes, users
from app.api.v1.endpoints.admin import (
    chat_rooms as admin_chat_rooms,
    user_recipes as admin_user_recipes,
    recipes as admin_recipes,
)

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    user_recipes.router,
    prefix="/user-recipes",
    tags=["user-recipes"],
)
api_router.include_router(
    admin_user_recipes.router,
    prefix="/admin/user-recipes",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
api_router.include_router(
    admin_recipes.router,
    prefix="/admin/recipes",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
api_router.include_router(
    admin_chat_rooms.router,
    prefix="/admin/chat-rooms",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
