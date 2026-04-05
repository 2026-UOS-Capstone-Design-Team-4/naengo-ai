# DB 테이블 베이스 클래스 및 모델 통합 관리
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 DB 모델의 기초가 되는 클래스"""
    pass


# 모든 모델을 여기에 임포트하여 Base.metadata.create_all()이 모든 테이블을 인식하게 합니다.
from app.models.chat import ChatRoom, SessionLog  # noqa
from app.models.recipe import Recipe, RecipeStats  # noqa
from app.models.social import Like, Scrap  # noqa
from app.models.user import User  # noqa
