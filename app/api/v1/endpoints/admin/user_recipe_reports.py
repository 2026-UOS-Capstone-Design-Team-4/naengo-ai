from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user
from app.api.v1.openapi.admin_user_recipe_reports import (
    GET_ADMIN_USER_RECIPE_REPORT_DESCRIPTION,
    GET_ADMIN_USER_RECIPE_REPORT_RESPONSES,
    GET_ADMIN_USER_RECIPE_REPORT_SUMMARY,
    GET_ADMIN_USER_RECIPE_REPORTS_DESCRIPTION,
    GET_ADMIN_USER_RECIPE_REPORTS_RESPONSES,
    GET_ADMIN_USER_RECIPE_REPORTS_SUMMARY,
    PATCH_ADMIN_USER_RECIPE_REPORT_DESCRIPTION,
    PATCH_ADMIN_USER_RECIPE_REPORT_RESPONSES,
    PATCH_ADMIN_USER_RECIPE_REPORT_SUMMARY,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user_recipe_report import (
    UserRecipeReportAdminUpdate,
    UserRecipeReportListResponse,
    UserRecipeReportResponse,
)
from app.services.user_recipe_report_service import (
    UserRecipeReportInvalidCursorError,
    UserRecipeReportService,
)

router = APIRouter()


@router.get(
    "",
    summary=GET_ADMIN_USER_RECIPE_REPORTS_SUMMARY,
    description=GET_ADMIN_USER_RECIPE_REPORTS_DESCRIPTION,
    response_model=UserRecipeReportListResponse,
    responses=GET_ADMIN_USER_RECIPE_REPORTS_RESPONSES,
)
def list_admin_user_recipe_reports(
    status: Literal["PENDING", "REVIEWING", "RESOLVED", "REJECTED"] | None = Query(
        default=None,
        description="신고 처리 상태로 필터링합니다.",
    ),
    user_recipe_id: int | None = Query(
        default=None,
        ge=1,
        description="특정 사용자 레시피 신고만 조회합니다.",
    ),
    reporter_user_id: int | None = Query(
        default=None,
        ge=1,
        description="특정 신고자의 신고만 조회합니다.",
    ),
    recipe_owner_user_id: int | None = Query(
        default=None,
        ge=1,
        description="특정 레시피 작성자가 받은 신고만 조회합니다.",
    ),
    cursor: str | None = Query(
        default=None,
        description="이전 응답의 `next_cursor` 값입니다.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="한 번에 조회할 개수입니다. 최대 100개입니다.",
    ),
    db: Session = Depends(get_db),
):
    service = UserRecipeReportService(db)
    try:
        items, next_cursor = service.get_admin_reports(
            status=status,
            user_recipe_id=user_recipe_id,
            reporter_user_id=reporter_user_id,
            recipe_owner_user_id=recipe_owner_user_id,
            cursor=cursor,
            limit=limit,
        )
    except UserRecipeReportInvalidCursorError:
        raise ApiError(400, "INVALID_CURSOR", "Cursor is invalid.") from None
    return UserRecipeReportListResponse(
        items=items,
        next_cursor=next_cursor,
        has_next=next_cursor is not None,
    )


@router.get(
    "/{report_id}",
    summary=GET_ADMIN_USER_RECIPE_REPORT_SUMMARY,
    description=GET_ADMIN_USER_RECIPE_REPORT_DESCRIPTION,
    response_model=UserRecipeReportResponse,
    responses=GET_ADMIN_USER_RECIPE_REPORT_RESPONSES,
)
def get_admin_user_recipe_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = UserRecipeReportService(db).get_admin_report(report_id)
    if not report:
        raise ApiError(
            404,
            "USER_RECIPE_REPORT_NOT_FOUND",
            "사용자 레시피 신고를 찾을 수 없습니다.",
        )
    return report


@router.patch(
    "/{report_id}",
    summary=PATCH_ADMIN_USER_RECIPE_REPORT_SUMMARY,
    description=PATCH_ADMIN_USER_RECIPE_REPORT_DESCRIPTION,
    response_model=UserRecipeReportResponse,
    responses=PATCH_ADMIN_USER_RECIPE_REPORT_RESPONSES,
)
def update_admin_user_recipe_report(
    report_id: int,
    body: UserRecipeReportAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = UserRecipeReportService(db).update_admin_report(
        report_id,
        body,
        current_user.user_id,
    )
    if not report:
        raise ApiError(
            404,
            "USER_RECIPE_REPORT_NOT_FOUND",
            "사용자 레시피 신고를 찾을 수 없습니다.",
        )
    return report
