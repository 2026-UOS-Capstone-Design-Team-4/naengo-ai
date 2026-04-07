# DB 테이블 베이스 클래스 및 모델 통합 관리
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 DB 모델의 기초가 되는 클래스"""
    pass
