from sqlalchemy import (
    BOOLEAN,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255))
    nickname = Column(String(50), unique=True, nullable=False)
    role = Column(String(20), default="USER")  # USER, ADMIN
    is_active = Column(BOOLEAN, nullable=False, default=True)
    is_blocked = Column(BOOLEAN, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 관계 설정
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    recipes = relationship("Recipe", back_populates="author")
    user_recipes = relationship(
        "UserRecipe",
        back_populates="user",
        foreign_keys="UserRecipe.user_id",
    )
    scraps = relationship("Scrap", back_populates="user")
    likes = relationship("Like", back_populates="user")
    chat_rooms = relationship("ChatRoom", back_populates="user")
    social_accounts = relationship(
        "SocialAccount",
        back_populates="user",
        order_by="SocialAccount.id",
    )

    @property
    def user_identities(self):
        return self.social_accounts


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )

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
    preferred_cooking_time_minutes = Column(Integer)
    serving_size = Column(Numeric(4, 1))
    recent_recipe_ids = Column(JSONB)
    ai_analyzed_at = Column(DateTime(timezone=True))

    @property
    def preferred_cooking_time(self) -> int | None:
        return self.preferred_cooking_time_minutes

    @preferred_cooking_time.setter
    def preferred_cooking_time(self, value: int | None) -> None:
        self.preferred_cooking_time_minutes = value

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 관계 설정
    user = relationship("User", back_populates="profile")
    facts = relationship(
        "UserProfileFact",
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class UserProfileFact(Base):
    __tablename__ = "user_profile_facts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "field",
            "canonical_value",
            "source_type",
            "source_key",
        ),
    )

    fact_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field = Column(String(50), nullable=False)
    canonical_value = Column(String(255), nullable=False)
    display_value = Column(String(255), nullable=False)
    source_type = Column(String(30), nullable=False)
    source_text = Column(String(1000), nullable=False)
    source_key = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("UserProfile", back_populates="facts")


# Register related models for standalone User imports.
from app.models.chat import ChatMessage, ChatRoom  # noqa: E402,F401
from app.models.recipe import Recipe, UserRecipe, UserRecipeReport  # noqa: E402,F401
from app.models.social import Like, Scrap, SocialAccount  # noqa: E402,F401
