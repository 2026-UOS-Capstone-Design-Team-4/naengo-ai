from enum import StrEnum

from pydantic import BaseModel


class PrimaryTask(StrEnum):
    RECIPE_FIND = "RECIPE_FIND"
    COOKING_QA = "COOKING_QA"
    PROFILE_MANAGEMENT = "PROFILE_MANAGEMENT"
    SERVICE_QA = "SERVICE_QA"
    SMALLTALK = "SMALLTALK"
    OFF_TOPIC = "OFF_TOPIC"


class InputMode(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class AnswerStrategy(StrEnum):
    CLARIFICATION = "CLARIFICATION"
    RECIPE_RECOMMENDATION = "RECIPE_RECOMMENDATION"
    RECIPE_CONTEXT_QA = "RECIPE_CONTEXT_QA"
    GENERAL_COOKING_QA = "GENERAL_COOKING_QA"
    SAFETY_COOKING_QA = "SAFETY_COOKING_QA"
    PROFILE_ACTION = "PROFILE_ACTION"
    FIXED = "FIXED"
    SMALLTALK = "SMALLTALK"


class RecipeFindSubIntent(StrEnum):
    BY_INGREDIENTS = "BY_INGREDIENTS"
    TARGET_DISH = "TARGET_DISH"
    DIET_CONSTRAINT = "DIET_CONSTRAINT"
    IMAGE_INGREDIENTS = "IMAGE_INGREDIENTS"
    QUICK_MEAL = "QUICK_MEAL"
    CLARIFICATION = "CLARIFICATION"


class CookingQASubIntent(StrEnum):
    RECIPE_CONTEXT = "RECIPE_CONTEXT"
    INGREDIENT_SUBSTITUTION = "INGREDIENT_SUBSTITUTION"
    TECHNIQUE = "TECHNIQUE"
    STORAGE = "STORAGE"
    SAFETY = "SAFETY"
    NUTRITION = "NUTRITION"
    GENERAL = "GENERAL"


class ProfileSubIntent(StrEnum):
    READ = "READ"
    UPSERT = "UPSERT"
    DELETE = "DELETE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


class ServiceQASubIntent(StrEnum):
    IDENTITY = "IDENTITY"
    USAGE = "USAGE"
    LIMITATION = "LIMITATION"


class MainIntentResult(BaseModel):
    primary_task: PrimaryTask
    input_modes: list[InputMode] = [InputMode.TEXT]
    confidence: float
    needs_clarification: bool = False
    clarification_question: str | None = None
    reason: str
