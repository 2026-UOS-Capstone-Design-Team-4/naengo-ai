from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.docs.admin_pending_recipes import (
    PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION,
    PATCH_ADMIN_PENDING_RECIPE_RESPONSES,
    PATCH_ADMIN_PENDING_RECIPE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.pending_recipe import PendingRecipeAdminUpdate, PendingRecipeResponse
from app.services.pending_recipe_service import (
    PendingRecipeApprovalError,
    PendingRecipeService,
)

router = APIRouter()


@router.patch(
    "/{pending_recipe_id}",
    summary=PATCH_ADMIN_PENDING_RECIPE_SUMMARY,
    description=PATCH_ADMIN_PENDING_RECIPE_DESCRIPTION,
    response_model=PendingRecipeResponse,
    responses=PATCH_ADMIN_PENDING_RECIPE_RESPONSES,
)
def update_pending_recipe_status(
    pending_recipe_id: int,
    body: PendingRecipeAdminUpdate,
    db: Session = Depends(get_db),
):
    pending_recipe_service = PendingRecipeService(db)
    try:
        pending = pending_recipe_service.update_pending_recipe_status(
            pending_recipe_id,
            body,
        )
    except PendingRecipeApprovalError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not pending:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")
    return pending
