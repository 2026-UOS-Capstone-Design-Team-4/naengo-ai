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
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep  # noqa: F401
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401


class RecipeSource(Base):
    __tablename__ = "recipe_sources"

    source_id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(30), nullable=False)
    source_site = Column(String(50), nullable=False)
    parser_type = Column(String(20), nullable=False)
    source_recipe_id = Column(String(100))
    source_url = Column(String(1024))
    source_author_name = Column(String(255))
    source_author_url = Column(String(1024))
    source_published_at = Column(DateTime(timezone=True))
    raw_payload = Column(JSONB, nullable=False, default=dict)
    raw_content_hash = Column(String(64))
    collection_status = Column(String(30), nullable=False, default="COLLECTED")
    parse_status = Column(String(30), nullable=False, default="NOT_PARSED")
    review_status = Column(String(30), nullable=False, default="PENDING")
    import_status = Column(String(30), nullable=False, default="NOT_IMPORTED")
    validation_errors = Column(JSONB, nullable=False, default=list)
    parser_version = Column(String(50))
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    parsed_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))
    imported_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    imported_recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="SET NULL"),
    )

    extraction = relationship(
        "RecipeSourceExtraction",
        back_populates="source",
        uselist=False,
        cascade="all, delete-orphan",
    )
    imported_recipe = relationship(
        "Recipe",
        foreign_keys=[imported_recipe_id],
        primaryjoin="RecipeSource.imported_recipe_id == Recipe.recipe_id",
    )
    image_generations = relationship("RecipeImageGeneration", back_populates="source")

    @property
    def status(self) -> str:
        if self.import_status == "IMPORTED":
            return "IMPORTED"
        if self.review_status == "REJECTED":
            return "REJECTED"
        if self.review_status == "APPROVED":
            return "READY"
        if self.parse_status in {"INVALID", "DUPLICATE", "REVIEW_REQUIRED"}:
            return self.parse_status
        if self.parse_status == "PARSED":
            return "PARSED"
        return self.collection_status

    @status.setter
    def status(self, value: str) -> None:
        if value == "COLLECTED":
            self.collection_status = "COLLECTED"
            self.parse_status = "NOT_PARSED"
            self.review_status = "PENDING"
            self.import_status = "NOT_IMPORTED"
        elif value == "PARSED":
            self.parse_status = "PARSED"
            self.review_status = "PENDING"
        elif value in {"INVALID", "DUPLICATE", "REVIEW_REQUIRED"}:
            self.parse_status = value
            self.review_status = "PENDING"
        elif value == "READY":
            self.parse_status = "PARSED"
            self.review_status = "APPROVED"
        elif value == "IMPORTED":
            self.import_status = "IMPORTED"
        elif value == "REJECTED":
            self.review_status = "REJECTED"
        else:
            self.collection_status = value

    @property
    def content_hash(self) -> str | None:
        return self.raw_content_hash

    @content_hash.setter
    def content_hash(self, value: str | None) -> None:
        self.raw_content_hash = value


class RecipeSourceExtraction(Base):
    __tablename__ = "recipe_source_extractions"

    extraction_id = Column(Integer, primary_key=True)
    source_id = Column(
        Integer,
        ForeignKey("recipe_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255))
    summary = Column(Text)
    description = Column(Text)
    servings = Column(Numeric(4, 1))
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    total_time_minutes = Column(Integer)
    calories = Column(Integer)
    difficulty = Column(String(10))
    difficulty_score = Column(Integer)
    source_main_image_url = Column(String(1024))
    source_thumbnail_url = Column(String(1024))
    source_video_url = Column(String(1024))
    content_hash = Column(String(64))
    completeness_score = Column(Numeric(5, 2))
    confidence_score = Column(Numeric(5, 2))
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("RecipeSource", back_populates="extraction")
    ingredients = relationship(
        "RecipeSourceExtractedIngredient",
        back_populates="extraction",
        order_by="RecipeSourceExtractedIngredient.sort_order",
        cascade="all, delete-orphan",
    )
    steps = relationship(
        "RecipeSourceExtractedStep",
        back_populates="extraction",
        order_by="RecipeSourceExtractedStep.step_no",
        cascade="all, delete-orphan",
    )
    labels = relationship(
        "RecipeSourceExtractedLabel",
        back_populates="extraction",
        order_by="RecipeSourceExtractedLabel.sort_order",
        cascade="all, delete-orphan",
    )


class RecipeSourceExtractedIngredient(Base):
    __tablename__ = "recipe_source_extracted_ingredients"

    extracted_ingredient_id = Column(Integer, primary_key=True)
    extraction_id = Column(
        Integer,
        ForeignKey("recipe_source_extractions.extraction_id", ondelete="CASCADE"),
        nullable=False,
    )
    group_name = Column(String(100))
    name = Column(String(100), nullable=False)
    normalized_name = Column(String(100))
    amount_text = Column(String(100))
    quantity = Column(Numeric(10, 3))
    unit = Column(String(50))
    note = Column(Text)
    raw_text = Column(Text)
    is_optional = Column(BOOLEAN, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)

    extraction = relationship("RecipeSourceExtraction", back_populates="ingredients")


class RecipeSourceExtractedStep(Base):
    __tablename__ = "recipe_source_extracted_steps"

    extracted_step_id = Column(Integer, primary_key=True)
    extraction_id = Column(
        Integer,
        ForeignKey("recipe_source_extractions.extraction_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_no = Column(Integer, nullable=False)
    title = Column(String(255))
    instruction = Column(Text, nullable=False)
    duration_minutes = Column(Integer)
    temperature = Column(String(50))
    equipment = Column(JSONB, nullable=False, default=list)
    source_image_url = Column(String(1024))
    tip = Column(Text)
    raw_text = Column(Text)
    sort_order = Column(Integer, nullable=False, default=0)

    extraction = relationship("RecipeSourceExtraction", back_populates="steps")


class RecipeSourceExtractedLabel(Base):
    __tablename__ = "recipe_source_extracted_labels"

    extracted_label_id = Column(Integer, primary_key=True)
    extraction_id = Column(
        Integer,
        ForeignKey("recipe_source_extractions.extraction_id", ondelete="CASCADE"),
        nullable=False,
    )
    label_type = Column(String(30), nullable=False)
    label_value = Column(Text, nullable=False)
    confidence_score = Column(Numeric(5, 2))
    source = Column(String(30), nullable=False, default="SCRAPE")
    sort_order = Column(Integer, nullable=False, default=0)

    extraction = relationship("RecipeSourceExtraction", back_populates="labels")


class RecipeImageGeneration(Base):
    __tablename__ = "recipe_image_generations"

    generation_id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
    )
    source_id = Column(
        Integer,
        ForeignKey("recipe_sources.source_id", ondelete="SET NULL"),
    )
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    status = Column(String(30), nullable=False, default="REQUESTED")
    generated_media_id = Column(
        Integer,
        ForeignKey("recipe_media.media_id", ondelete="SET NULL"),
    )
    error_message = Column(Text)
    generation_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    selected_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship("Recipe", back_populates="image_generations")
    source = relationship("RecipeSource", back_populates="image_generations")
    media = relationship(
        "RecipeMedia",
        foreign_keys="RecipeMedia.generation_id",
        back_populates="generation",
    )
