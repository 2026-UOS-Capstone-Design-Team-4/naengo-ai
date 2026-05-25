import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.deps import get_current_user_id
from app.api.v1.openapi.user_recipe_reports import (
    POST_USER_RECIPE_REPORT_DESCRIPTION,
    POST_USER_RECIPE_REPORT_RESPONSES,
    POST_USER_RECIPE_REPORT_SUMMARY,
)
from app.api.v1.openapi.user_recipes import (
    DELETE_USER_RECIPE_DESCRIPTION,
    DELETE_USER_RECIPE_RESPONSES,
    DELETE_USER_RECIPE_SUMMARY,
    GET_APPROVED_USER_RECIPE_DESCRIPTION,
    GET_APPROVED_USER_RECIPE_RESPONSES,
    GET_APPROVED_USER_RECIPE_SUMMARY,
    GET_APPROVED_USER_RECIPES_DESCRIPTION,
    GET_APPROVED_USER_RECIPES_RESPONSES,
    GET_APPROVED_USER_RECIPES_SUMMARY,
    GET_USER_RECIPE_DESCRIPTION,
    GET_USER_RECIPE_RESPONSES,
    GET_USER_RECIPE_SUMMARY,
    GET_USER_RECIPES_DESCRIPTION,
    GET_USER_RECIPES_RESPONSES,
    GET_USER_RECIPES_SUMMARY,
    POST_USER_RECIPE_DESCRIPTION,
    POST_USER_RECIPE_RESPONSES,
    POST_USER_RECIPE_SUMMARY,
)
from app.db.session import get_db
from app.schemas.user_recipe import (
    UserRecipeCreate,
    UserRecipeListItemResponse,
    UserRecipePublicListResponse,
    UserRecipePublicResponse,
    UserRecipeResponse,
)
from app.schemas.user_recipe_report import (
    UserRecipeReportCreate,
    UserRecipeReportResponse,
)
from app.services.storage_service import user_recipe_image_storage
from app.services.user_recipe_report_service import (
    UserRecipeReportAlreadyExistsError,
    UserRecipeReportNotFoundError,
    UserRecipeReportOwnRecipeError,
    UserRecipeReportService,
)
from app.services.user_recipe_service import (
    UserRecipeImageUpload,
    UserRecipeImageValidationError,
    UserRecipeInvalidCursorError,
    UserRecipeService,
    UserRecipeStorageError,
)

router = APIRouter()


@router.get(
    "",
    summary=GET_APPROVED_USER_RECIPES_SUMMARY,
    description=GET_APPROVED_USER_RECIPES_DESCRIPTION,
    response_model=UserRecipePublicListResponse,
    responses=GET_APPROVED_USER_RECIPES_RESPONSES,
)
def get_approved_user_recipes(
    cursor: str | None = Query(
        default=None,
        description="이전 응답의 next_cursor. base64url JSON cursor입니다.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="한 번에 가져올 사용자 레시피 개수",
    ),
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    try:
        items, next_cursor = UserRecipeService(db).get_approved_user_recipes(
            cursor,
            limit,
        )
    except UserRecipeInvalidCursorError:
        raise ApiError(400, "INVALID_CURSOR", "Cursor is invalid.") from None
    return UserRecipePublicListResponse(
        items=items,
        next_cursor=next_cursor,
        has_next=next_cursor is not None,
    )


@router.get(
    "/me",
    summary=GET_USER_RECIPES_SUMMARY,
    description=GET_USER_RECIPES_DESCRIPTION,
    response_model=list[UserRecipeListItemResponse],
    responses=GET_USER_RECIPES_RESPONSES,
)
def get_user_recipes(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return UserRecipeService(db).get_user_recipes(current_user_id)


@router.get(
    "/me/{user_recipe_id}",
    summary=GET_USER_RECIPE_SUMMARY,
    description=GET_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipeResponse,
    responses=GET_USER_RECIPE_RESPONSES,
)
def get_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    recipe = UserRecipeService(db).get_user_recipe(user_recipe_id, current_user_id)
    if not recipe:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return recipe


@router.post(
    "/me",
    summary=POST_USER_RECIPE_SUMMARY,
    description=POST_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipeResponse,
    responses=POST_USER_RECIPE_RESPONSES,
    status_code=201,
)
def create_user_recipe(
    payload: str = Form(...),
    main_image: UploadFile | None = File(default=None),
    step_images: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        body = UserRecipeCreate.model_validate(json.loads(payload))
    except json.JSONDecodeError as exc:
        raise ApiError(
            422,
            "VALIDATION_FAILED",
            "payload must be valid JSON.",
        ) from exc
    except ValidationError as exc:
        raise ApiError(
            422,
            "VALIDATION_FAILED",
            "payload is invalid.",
            {"fields": exc.errors(include_context=False)},
        ) from exc

    has_image = bool(main_image or step_images)
    if has_image and not user_recipe_image_storage.is_available:
        raise ApiError(
            503,
            "STORAGE_NOT_CONFIGURED",
            "이미지 업로드를 위한 스토리지가 설정되지 않았습니다.",
        )

    try:
        recipe = UserRecipeService(db).create_user_recipe(
            body,
            current_user_id,
            main_image=_to_image_upload(main_image) if main_image else None,
            step_images=[_to_image_upload(image) for image in (step_images or [])],
        )
    except UserRecipeStorageError as exc:
        raise ApiError(
            503, "STORAGE_ERROR", "이미지 스토리지를 사용할 수 없습니다."
        ) from exc
    except UserRecipeImageValidationError as exc:
        raise ApiError(422, "INVALID_IMAGE", str(exc)) from exc
    if not recipe:
        raise ApiError(404, "RESOURCE_NOT_FOUND", "사용자를 찾을 수 없습니다.")
    return recipe


@router.delete(
    "/me/{user_recipe_id}",
    summary=DELETE_USER_RECIPE_SUMMARY,
    description=DELETE_USER_RECIPE_DESCRIPTION,
    responses=DELETE_USER_RECIPE_RESPONSES,
)
def delete_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    deleted = UserRecipeService(db).delete_user_recipe(user_recipe_id, current_user_id)
    if not deleted:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return {"message": "레시피가 삭제되었습니다."}


@router.post(
    "/{user_recipe_id}/reports",
    summary=POST_USER_RECIPE_REPORT_SUMMARY,
    description=POST_USER_RECIPE_REPORT_DESCRIPTION,
    response_model=UserRecipeReportResponse,
    responses=POST_USER_RECIPE_REPORT_RESPONSES,
    status_code=201,
)
def report_user_recipe(
    user_recipe_id: int,
    body: UserRecipeReportCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        return UserRecipeReportService(db).create_report(
            user_recipe_id,
            current_user_id,
            body,
        )
    except UserRecipeReportNotFoundError:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "신고 가능한 사용자 레시피를 찾을 수 없습니다.",
        ) from None
    except UserRecipeReportOwnRecipeError:
        raise ApiError(
            409,
            "CANNOT_REPORT_OWN_RECIPE",
            "본인이 작성한 레시피는 신고할 수 없습니다.",
        ) from None
    except UserRecipeReportAlreadyExistsError:
        raise ApiError(
            409,
            "ALREADY_REPORTED",
            "이미 신고한 사용자 레시피입니다.",
        ) from None


@router.get(
    "/{user_recipe_id}",
    summary=GET_APPROVED_USER_RECIPE_SUMMARY,
    description=GET_APPROVED_USER_RECIPE_DESCRIPTION,
    response_model=UserRecipePublicResponse,
    responses=GET_APPROVED_USER_RECIPE_RESPONSES,
)
def get_approved_user_recipe(
    user_recipe_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    recipe = UserRecipeService(db).get_approved_user_recipe(user_recipe_id)
    if not recipe:
        raise ApiError(
            404,
            "USER_RECIPE_NOT_FOUND",
            "제출 레시피를 찾을 수 없습니다.",
        )
    return recipe


def _to_image_upload(file: UploadFile) -> UserRecipeImageUpload:
    return UserRecipeImageUpload(
        filename=file.filename or "image",
        content_type=file.content_type or "application/octet-stream",
        data=file.file.read(),
    )
