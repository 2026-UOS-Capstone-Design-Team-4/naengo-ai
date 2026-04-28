import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.api.v1.api import api_router
from app.db.session import init_db

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    앱의 시작과 종료 시점에 실행되는 로직입니다.
    """
    # 1. 앱 시작 시 실행 (startup)
    try:
        logger.info("데이터베이스를 초기화하는 중...")
        # pgvector 확장 활성화 (vector 익스텐션이 필요할 때)
        init_db()

        logger.info("데이터베이스 초기화 완료.")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 에러 발생: {e}")
        # DB 연결 실패 시 앱 실행을 중단하고 싶지 않다면 이대로 둡니다.

    yield

    # 2. 앱 종료 시 실행 (shutdown)
    logger.info("애플리케이션을 종료합니다.")


app = FastAPI(
    title="냉고 AI API",
    description=(
        "냉고(Naengo)는 냉장고 속 재료로 레시피를 추천해주는 AI 요리 어시스턴트입니다.\n\n"
        "## 주요 기능\n"
        "- **채팅**: 재료를 입력하면 AI가 레시피를 추천 (SSE 스트리밍)\n"
        "- **레시피**: 벡터 유사도 기반 레시피 검색\n"
        "- **어드민**: 레시피 관리"
    ),
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "chat",
            "description": "AI 레시피 추천 채팅. SSE 스트리밍 방식으로 응답합니다.",
        },
        {
            "name": "recipes",
            "description": "레시피 조회 및 검색 API.",
        },
        {
            "name": "admin",
            "description": "관리자 전용 API. 레시피 등록 및 관리에 사용합니다.",
        },
    ],
)


# Scalar API Reference (더 예쁜 문서 도구)
@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


# CORS 설정 (프론트엔드 연결을 위해 모든 도메인 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "ok", "message": "Naengo AI API is running"}
