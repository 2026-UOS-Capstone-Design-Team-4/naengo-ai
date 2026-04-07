import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.api.v1.api import api_router
from app.db.session import engine, init_db
from app.models.base import Base

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
        
        # 모든 모델을 임포트하여 Base.metadata가 테이블들을 인식하게 합니다.
        from app.models.chat import ChatRoom, SessionLog  # noqa
        from app.models.recipe import Recipe, RecipeStats  # noqa
        from app.models.social import Like, Scrap  # noqa
        from app.models.user import User  # noqa
        
        # 모든 테이블 생성 (테이블이 이미 있으면 무시됨)
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 초기화 완료.")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 에러 발생: {e}")
        # DB 연결 실패 시 앱 실행을 중단하고 싶지 않다면 이대로 둡니다.

    yield

    # 2. 앱 종료 시 실행 (shutdown)
    logger.info("애플리케이션을 종료합니다.")


app = FastAPI(
    title="Naengo AI API",
    docs_url=None,  # 기본 Swagger UI 비활성화
    redoc_url=None,  # 기본 ReDoc 비활성화
    lifespan=lifespan,  # lifespan 이벤트 등록
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
