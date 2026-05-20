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


def _as_list(value):
    return value if isinstance(value, list) else []


def _default_pending_recipe_payload():
    return {
        "description": None,
        "ingredients": [],
        "ingredients_raw": [],
        "instructions": [],
        "servings": None,
        "cooking_time_minutes": None,
        "kcal_per_serving": None,
        "difficulty": None,
        "category": [],
        "tags": [],
        "tips": [],
        "video_url": None,
        "image_url": None,
    }


class Recipe(Base):
    __tablename__ = "recipes"

    recipe_id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        Integer,
        ForeignKey("recipe_sources.source_id", ondelete="SET NULL"),
    )
    title = Column(String(255), nullable=False)
    summary = Column(Text)
    description = Column(Text, nullable=False)
    servings = Column(Numeric(4, 1), nullable=False)
    cooking_time_minutes = Column(Integer, nullable=False)
    kcal_per_serving = Column(Integer)
    difficulty = Column(String(10), nullable=False)
    visibility = Column(String(20), nullable=False, default="PUBLIC")
    author_type = Column(String(20), nullable=False, default="ADMIN")
    author_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    classification_status = Column(
        String(30),
        nullable=False,
        default="NOT_CLASSIFIED",
    )
    classified_at = Column(DateTime(timezone=True))
    is_active = Column(BOOLEAN, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User", back_populates="recipes")
    stats = relationship("RecipeStats", back_populates="recipe", uselist=False)
    scraps = relationship("Scrap", back_populates="recipe")
    likes = relationship("Like", back_populates="recipe")
    source = relationship(
        "RecipeSource",
        foreign_keys=[source_id],
        primaryjoin="Recipe.source_id == RecipeSource.source_id",
    )
    ingredients_list = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        order_by="RecipeIngredient.sort_order",
        cascade="all, delete-orphan",
    )
    steps = relationship(
        "RecipeStep",
        back_populates="recipe",
        order_by="RecipeStep.step_no",
        cascade="all, delete-orphan",
    )
    labels = relationship(
        "RecipeLabel",
        back_populates="recipe",
        order_by="RecipeLabel.sort_order",
        cascade="all, delete-orphan",
    )
    nutrition = relationship(
        "RecipeNutrition",
        back_populates="recipe",
        uselist=False,
        cascade="all, delete-orphan",
    )
    classifications = relationship(
        "RecipeClassification",
        back_populates="recipe",
        uselist=False,
        cascade="all, delete-orphan",
    )
    media = relationship(
        "RecipeMedia",
        back_populates="recipe",
        order_by="RecipeMedia.sort_order",
        cascade="all, delete-orphan",
        foreign_keys="RecipeMedia.recipe_id",
    )
    image_generations = relationship("RecipeImageGeneration", back_populates="recipe")
    embeddings = relationship(
        "RecipeEmbedding",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )

    @property
    def content(self) -> str | None:
        return self.summary or self.description

    @content.setter
    def content(self, value: str | None) -> None:
        if value and not self.summary:
            self.summary = value

    @property
    def ingredients(self) -> list[dict]:
        return [
            {
                "name": item.name,
                "amount": item.amount_text,
                "unit": item.unit or "",
                "type": item.group_name or "",
                "note": item.note,
            }
            for item in self.ingredients_list
        ]

    @ingredients.setter
    def ingredients(self, value: list[dict] | None) -> None:
        self.ingredients_list = [
            RecipeIngredient(
                name=item.get("name", ""),
                amount_text=str(item.get("amount") or item.get("amount_text") or ""),
                unit=item.get("unit"),
                group_name=item.get("type") or item.get("group_name"),
                note=item.get("note"),
                raw_text=item.get("raw_text"),
                sort_order=index,
            )
            for index, item in enumerate(_as_list(value))
            if isinstance(item, dict)
        ]

    @property
    def ingredients_raw(self) -> str:
        return ", ".join(
            " ".join(part for part in [item.name, item.amount_text] if part)
            for item in self.ingredients_list
        )

    @ingredients_raw.setter
    def ingredients_raw(self, value: str | None) -> None:
        # Kept for API compatibility. Structured ingredients are stored separately.
        return None

    @property
    def instructions(self) -> list[str]:
        return [step.instruction for step in self.steps]

    @instructions.setter
    def instructions(self, value: list[str | dict] | None) -> None:
        steps = []
        for index, item in enumerate(_as_list(value), start=1):
            if isinstance(item, dict):
                instruction = item.get("instruction", "")
                step_no = int(item.get("step_no") or index)
            else:
                instruction = str(item)
                step_no = index
            steps.append(
                RecipeStep(step_no=step_no, instruction=instruction, sort_order=index)
            )
        self.steps = steps

    @property
    def category(self) -> list[str]:
        return [
            label.label_value
            for label in self.labels
            if label.label_type == "CATEGORY"
        ]

    @category.setter
    def category(self, value: list[str] | None) -> None:
        self._replace_labels("CATEGORY", value or [])

    @property
    def tags(self) -> list[str]:
        return [label.label_value for label in self.labels if label.label_type == "TAG"]

    @tags.setter
    def tags(self, value: list[str] | None) -> None:
        self._replace_labels("TAG", value or [])

    @property
    def tips(self) -> list[str]:
        return [label.label_value for label in self.labels if label.label_type == "TIP"]

    @tips.setter
    def tips(self, value: list[str] | None) -> None:
        self._replace_labels("TIP", value or [])

    @property
    def video_url(self) -> str | None:
        media = next((item for item in self.media if item.media_type == "VIDEO"), None)
        return media.storage_url if media else None

    @video_url.setter
    def video_url(self, value: str | None) -> None:
        if value:
            self.media.append(
                RecipeMedia(media_type="VIDEO", source_url=value, storage_url=value)
            )

    @property
    def image_url(self) -> str | None:
        media = next(
            (
                item
                for item in self.media
                if item.media_type == "IMAGE"
                and item.image_role == "MAIN"
                and item.is_primary
            ),
            None,
        )
        if media is None:
            media = next(
                (
                    item
                    for item in self.media
                    if item.media_type == "IMAGE" and item.image_role == "MAIN"
                ),
                None,
            )
        return media.storage_url if media else None

    @image_url.setter
    def image_url(self, value: str | None) -> None:
        if value:
            self.media.append(
                RecipeMedia(
                    media_type="IMAGE",
                    image_role="MAIN",
                    source_url=value,
                    storage_url=value,
                    is_primary=True,
                )
            )

    @property
    def embedding(self) -> list[float] | None:
        item = next(
            (
                embedding
                for embedding in self.embeddings
                if embedding.embedding_type == "RECIPE_SEARCH"
            ),
            None,
        )
        return item.embedding if item else None

    @embedding.setter
    def embedding(self, value: list[float] | None) -> None:
        if value is not None:
            self.embeddings = [
                RecipeEmbedding(
                    embedding_type="RECIPE_SEARCH",
                    model="text-embedding-3-small",
                    content_hash="pending",
                    embedding=value,
                )
            ]

    def _replace_labels(self, label_type: str, values: list[str]) -> None:
        self.labels = [
            label for label in self.labels if label.label_type != label_type
        ] + [
            RecipeLabel(
                label_type=label_type,
                label_value=value,
                source="ADMIN",
                sort_order=index,
            )
            for index, value in enumerate(values)
        ]


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    ingredient_id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
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

    recipe = relationship("Recipe", back_populates="ingredients_list")

    @property
    def amount(self) -> str | None:
        return self.amount_text

    @amount.setter
    def amount(self, value: str | None) -> None:
        self.amount_text = value


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    step_id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_no = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    tip = Column(Text)
    sort_order = Column(Integer, nullable=False, default=0)

    recipe = relationship("Recipe", back_populates="steps")
    media = relationship("RecipeMedia", back_populates="step")


class RecipeLabel(Base):
    __tablename__ = "recipe_labels"

    label_id = Column(Integer, primary_key=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    label_type = Column(String(30), nullable=False)
    label_value = Column(Text, nullable=False)
    source = Column(String(30), nullable=False, default="SCRAPE")
    confidence_score = Column(Numeric(5, 2))
    sort_order = Column(Integer, nullable=False, default=0)

    recipe = relationship("Recipe", back_populates="labels")


class RecipeNutrition(Base):
    __tablename__ = "recipe_nutrition"

    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
    )
    serving_weight_grams = Column(Numeric(10, 2))
    kcal_per_serving = Column(Integer)
    carbohydrate_grams = Column(Numeric(10, 2))
    protein_grams = Column(Numeric(10, 2))
    fat_grams = Column(Numeric(10, 2))
    sodium_milligrams = Column(Numeric(10, 2))
    source = Column(String(30), nullable=False, default="SOURCE")
    raw_payload = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship("Recipe", back_populates="nutrition")


class RecipeClassification(Base):
    __tablename__ = "recipe_classifications"

    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
    )
    cuisine_type = Column(String(50))
    dish_type = Column(String(50))
    cooking_methods = Column(JSONB, nullable=False, default=list)
    meal_types = Column(JSONB, nullable=False, default=list)
    occasions = Column(JSONB, nullable=False, default=list)
    situations = Column(JSONB, nullable=False, default=list)
    main_ingredients = Column(JSONB, nullable=False, default=list)
    taste_keywords = Column(JSONB, nullable=False, default=list)
    texture_keywords = Column(JSONB, nullable=False, default=list)
    diet_keywords = Column(JSONB, nullable=False, default=list)
    allergen_keywords = Column(JSONB, nullable=False, default=list)
    equipment = Column(JSONB, nullable=False, default=list)
    season = Column(JSONB, nullable=False, default=list)
    category_labels = Column(JSONB, nullable=False, default=list)
    classification_source = Column(String(30), nullable=False, default="RULE")
    confidence_score = Column(Numeric(5, 2))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship("Recipe", back_populates="classifications")


class RecipeMedia(Base):
    __tablename__ = "recipe_media"

    media_id = Column(Integer, primary_key=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id = Column(Integer, ForeignKey("recipe_steps.step_id", ondelete="CASCADE"))
    media_type = Column(String(20), nullable=False)
    image_role = Column(String(30))
    source_url = Column(String(1024))
    storage_url = Column(String(1024), nullable=False)
    thumbnail_url = Column(String(1024))
    width = Column(Integer)
    height = Column(Integer)
    file_size_bytes = Column(Integer)
    mime_type = Column(String(100))
    storage_provider = Column(String(30), nullable=False, default="S3")
    generation_id = Column(
        Integer,
        ForeignKey("recipe_image_generations.generation_id", ondelete="SET NULL"),
    )
    is_primary = Column(BOOLEAN, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship(
        "Recipe",
        back_populates="media",
        foreign_keys=[recipe_id],
    )
    step = relationship("RecipeStep", back_populates="media")
    generation = relationship(
        "RecipeImageGeneration",
        foreign_keys=[generation_id],
        back_populates="media",
    )


class RecipeEmbedding(Base):
    __tablename__ = "recipe_embeddings"

    embedding_id = Column(Integer, primary_key=True)
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding_type = Column(String(30), nullable=False, default="RECIPE_SEARCH")
    model = Column(String(100), nullable=False)
    content_hash = Column(String(64), nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship("Recipe", back_populates="embeddings")


class PendingRecipe(Base):
    __tablename__ = "user_recipes"

    pending_recipe_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    submission_text = Column(Text, nullable=False)
    draft_payload = Column(
        JSONB,
        nullable=False,
        default=_default_pending_recipe_payload,
    )
    ai_suggested_patch = Column(
        JSONB,
        nullable=False,
        default=_default_pending_recipe_payload,
    )
    validation_errors = Column(JSONB, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="PENDING")
    import_status = Column(String(30), nullable=False, default="NOT_IMPORTED")
    is_active = Column(BOOLEAN, nullable=False, default=True)
    admin_note = Column(Text)
    rejection_reason = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    imported_recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="SET NULL"),
    )
    imported_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User",
        back_populates="pending_recipes",
        foreign_keys=[user_id],
    )
    imported_recipe = relationship("Recipe", foreign_keys=[imported_recipe_id])


class RecipeQualityScore(Base):
    __tablename__ = "recipe_quality_scores"

    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
    )
    completeness_score = Column(Numeric(5, 2))
    image_quality_score = Column(Numeric(5, 2))
    instruction_quality_score = Column(Numeric(5, 2))
    nutrition_confidence = Column(Numeric(5, 2))
    classification_confidence = Column(Numeric(5, 2))
    duplicate_score = Column(Numeric(5, 2))
    reviewed_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class RecipeStats(Base):
    __tablename__ = "recipe_stats"

    recipe_id = Column(
        Integer,
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
    )
    likes_count = Column(Integer, nullable=False, default=0)
    scrap_count = Column(Integer, nullable=False, default=0)

    recipe = relationship("Recipe", back_populates="stats")


from app.models.recipe_source import RecipeSource  # noqa: E402,F401
