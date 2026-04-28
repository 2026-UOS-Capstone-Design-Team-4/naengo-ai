from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BOOLEAN,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
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
    description = Column(Text, nullable=False)
    ingredients = Column(JSONB, nullable=False)
    ingredients_raw = Column(Text, nullable=False)
    instructions = Column(JSONB, nullable=False)
    servings = Column(Numeric(4, 1), nullable=False)
    cooking_time = Column(Integer, nullable=False)
    calories = Column(Integer)
    difficulty = Column(String(10), nullable=False)  # easy, normal, hard
    category = Column(JSONB, nullable=False)
    tags = Column(JSONB, nullable=False, default=list)
    tips = Column(JSONB, nullable=False, default=list)
    content = Column(Text)
    video_url = Column(String(512))
    image_url = Column(String(512))
    is_active = Column(BOOLEAN, nullable=False, default=True)
    author_type = Column(String(20), nullable=False, default="ADMIN")  # ADMIN, USER
    author_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding = Column(Vector(1536))

    # 관계 설정
    author = relationship("User", back_populates="recipes")
    stats = relationship("RecipeStats", back_populates="recipe", uselist=False)
    scraps = relationship("Scrap", back_populates="recipe")
    likes = relationship("Like", back_populates="recipe")


class PendingRecipe(Base):
    __tablename__ = "pending_recipes"

    pending_recipe_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    ingredients = Column(JSONB)
    ingredients_raw = Column(Text)
    instructions = Column(JSONB)
    servings = Column(Numeric(4, 1))
    cooking_time = Column(Integer)
    calories = Column(Integer)
    difficulty = Column(String(10))
    category = Column(JSONB)
    tags = Column(JSONB)
    tips = Column(JSONB)
    video_url = Column(String(512))
    image_url = Column(String(512))
    is_active = Column(BOOLEAN, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED
    admin_note = Column(Text)
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="pending_recipes")


class RecipeStats(Base):
    __tablename__ = "recipe_stats"

    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True
    )
    likes_count = Column(Integer, nullable=False, default=0)
    scrap_count = Column(Integer, nullable=False, default=0)

    # 관계 설정
    recipe = relationship("Recipe", back_populates="stats")
