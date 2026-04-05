from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class Scrap(Base):
    __tablename__ = "scraps"

    scrap_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 중복 스크랩 방지
    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_user_recipe_scrap"),)

    # 관계 설정
    user = relationship("User", back_populates="scraps")
    recipe = relationship("Recipe", back_populates="scraps")


class Like(Base):
    __tablename__ = "likes"

    like_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 중복 좋아요 방지
    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_user_recipe_like"),)

    # 관계 설정
    user = relationship("User", back_populates="likes")
    recipe = relationship("Recipe", back_populates="likes")
