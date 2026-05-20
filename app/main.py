import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.api.errors import register_error_handlers
from app.api.v1.api import api_router
from app.db.session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작과 종료 시점에 필요한 작업을 수행합니다.
    """
    try:
        logger.info("데이터베이스를 초기화하는 중입니다.")
        init_db()
        logger.info("데이터베이스 초기화가 완료되었습니다.")
    except Exception as e:
        logger.error("데이터베이스 초기화 중 오류가 발생했습니다: %s", e)

    yield

    logger.info("애플리케이션을 종료합니다.")


app = FastAPI(
    title="냉고 AI API",
    description=(
        "냉고(Naengo)는 냉장고 속 재료와 사용자 취향을 바탕으로 "
        "레시피를 추천하는 AI 요리 어시스턴트입니다.\n\n"
        "## 주요 기능\n"
        "- **채팅**: 재료와 상황을 입력하면 AI가 레시피를 추천합니다. 응답은 SSE로 스트리밍됩니다.\n"
        "- **레시피**: 최신순/좋아요순 목록, 단건 상세, 좋아요, 스크랩 API를 제공합니다.\n"
        "- **사용자**: 사용자 정보와 프로필 취향 입력을 관리합니다.\n"
        "- **제출 레시피**: 사용자가 직접 레시피를 제출하고 관리자가 승인할 수 있습니다.\n"
        "- **관리자**: 제출 레시피 검토와 승인 흐름을 제공합니다.\n\n"
        "## 인증\n"
        "> 현재 실제 사용자 인증은 구현되어 있지 않습니다. "
        "모든 API는 임시로 `.env`의 `TEMP_USER_ID` 값을 현재 사용자로 사용합니다."
    ),
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "chat",
            "description": "채팅방 관리와 AI 레시피 추천 채팅 API입니다. 메시지 전송은 SSE 스트리밍 방식으로 응답합니다.",
        },
        {
            "name": "recipes",
            "description": "레시피 목록/상세 조회, 좋아요, 스크랩 API입니다.",
        },
        {
            "name": "users",
            "description": "사용자 정보, 프로필, 내 스크랩 레시피 조회 API입니다.",
        },
        {
            "name": "user-recipes",
            "description": "사용자가 제출한 레시피를 조회, 생성, 삭제하는 API입니다.",
        },
        {
            "name": "admin",
            "description": "관리자 전용 API입니다. 제출 레시피 검토와 승인에 사용합니다.",
        },
        {
            "name": "health",
            "description": "서버 상태 확인 API입니다.",
        },
    ],
)
register_error_handlers(app)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/",
    summary="상태 체크",
    description="서버가 정상 동작 중인지 확인합니다.",
    tags=["health"],
    responses={
        200: {
            "description": "서버 정상",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "message": "Naengo AI API is running"}
                }
            },
        }
    },
)
async def root():
    return {"status": "ok", "message": "Naengo AI API is running"}
