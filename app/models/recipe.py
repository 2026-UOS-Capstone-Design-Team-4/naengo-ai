from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Recipe(Base):
    __tablename__ = "recipes"

    recipe_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    ingredients_raw = Column(Text)
    ingredients = Column(JSONB)
    instructions = Column(JSONB)
    image_url = Column(String(512))
    video_url = Column(String(512))
    source = Column(String(20), default="STANDARD")  # STANDARD, USER
    author_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    status = Column(String(20), default="PENDING")  # APPROVED, PENDING, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # text-embedding-3-small (1536 차원) 기준
    embedding = Column(Vector(1536))

    # 관계 설정
    author = relationship("User", back_populates="recipes")
    stats = relationship("RecipeStats", back_populates="recipe", uselist=False)
    scraps = relationship("Scrap", back_populates="recipe")
    likes = relationship("Like", back_populates="recipe")


class RecipeStats(Base):
    __tablename__ = "recipe_stats"

    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True
    )
    likes_count = Column(Integer, default=0)
    scrap_count = Column(Integer, default=0)

    # 관계 설정
    recipe = relationship("Recipe", back_populates="stats")
