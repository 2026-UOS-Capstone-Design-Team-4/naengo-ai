from sqlalchemy import BOOLEAN, Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), unique=True, nullable=False)
    role = Column(String(20), default="USER")
    is_blocked = Column(BOOLEAN, default=False)
    preferences = Column(JSONB)  # 선호도, 알레르기 등
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    recipes = relationship("Recipe", back_populates="author")
    scraps = relationship("Scrap", back_populates="user")
    likes = relationship("Like", back_populates="user")
    chat_rooms = relationship("ChatRoom", back_populates="user")
