from sqlalchemy import BOOLEAN, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), unique=True, nullable=False)
    role = Column(String(20), default="USER")  # USER, ADMIN
    is_active = Column(BOOLEAN, nullable=False, default=True)
    is_blocked = Column(BOOLEAN, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    recipes = relationship("Recipe", back_populates="author")
    pending_recipes = relationship("PendingRecipe", back_populates="user")
    scraps = relationship("Scrap", back_populates="user")
    likes = relationship("Like", back_populates="user")
    chat_rooms = relationship("ChatRoom", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)

    # 유저 직접 입력 (문장 배열)
    user_input = Column(JSONB, nullable=False, default=list)

    # AI 분석 데이터
    allergies = Column(JSONB)
    dietary_restrictions = Column(JSONB)
    preferred_ingredients = Column(JSONB)
    disliked_ingredients = Column(JSONB)
    preferred_categories = Column(JSONB)
    frequently_used_ingredients = Column(JSONB)
    taste_keywords = Column(JSONB)
    cooking_skill = Column(String(10))       # easy, normal, hard
    preferred_cooking_time = Column(Integer)
    serving_size = Column(Numeric(4, 1))
    recent_recipe_ids = Column(JSONB)
    ai_analyzed_at = Column(DateTime(timezone=True))

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="profile")
