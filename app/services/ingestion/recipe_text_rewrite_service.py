import logging
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core import config
from app.models.recipe_source import RecipeSourceExtraction

logger = logging.getLogger(__name__)


class RecipeTextRewriteError(Exception):
    pass


@dataclass(frozen=True)
class IngredientTextDraft:
    group_name: str | None
    name: str
    normalized_name: str | None
    amount_text: str | None
    quantity: Any
    unit: str | None
    note: str | None
    raw_text: str | None
    is_optional: bool
    sort_order: int


@dataclass(frozen=True)
class StepTextDraft:
    step_no: int
    instruction: str
    source_image_url: str | None
    tip: str | None
    sort_order: int


@dataclass(frozen=True)
class RecipeTextDraft:
    title: str
    summary: str | None
    description: str
    ingredients: list[IngredientTextDraft]
    steps: list[StepTextDraft]
    tips: list[str]


class StepRewriteOutput(BaseModel):
    instruction: str
    tip: str | None = None


class RecipeRewriteOutput(BaseModel):
    title: str
    summary: str | None = None
    description: str
    steps: list[StepRewriteOutput]
    tips: list[str] = []


class RecipeTextRewriter(Protocol):
    def rewrite(self, extraction: RecipeSourceExtraction) -> RecipeTextDraft:
        pass


class PassthroughRecipeTextRewriter:
    def rewrite(self, extraction: RecipeSourceExtraction) -> RecipeTextDraft:
        return draft_from_extraction(extraction)


class AIRecipeTextRewriter:
    def __init__(
        self,
        agent: Agent | None = None,
        model: str = config.MODEL_NAME,
        enabled: bool = config.RECIPE_IMPORT_REWRITE_ENABLED,
        timeout_seconds: float = config.RECIPE_IMPORT_AI_TIMEOUT_SECONDS,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._agent = agent or _build_agent(model, timeout_seconds=timeout_seconds)
        self.enabled = enabled

    def rewrite(self, extraction: RecipeSourceExtraction) -> RecipeTextDraft:
        original = draft_from_extraction(extraction)
        if not self.enabled:
            logger.warning(
                "recipe import text rewrite is disabled; using extraction text"
            )
            return original

        try:
            result = self._agent.run_sync(_extraction_prompt(extraction))
        except Exception as exc:
            raise RecipeTextRewriteError("AI rewrite failed") from exc
        return _draft_from_rewrite_output(original, result.output)


def draft_from_extraction(extraction: RecipeSourceExtraction) -> RecipeTextDraft:
    tips = [
        label.label_value
        for label in extraction.labels
        if label.label_type == "TIP" and label.label_value
    ]
    return RecipeTextDraft(
        title=extraction.title,
        summary=extraction.summary,
        description=extraction.description or extraction.summary or extraction.title,
        ingredients=[
            IngredientTextDraft(
                group_name=ingredient.group_name,
                name=ingredient.name,
                normalized_name=ingredient.normalized_name,
                amount_text=ingredient.amount_text,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                note=ingredient.note,
                raw_text=ingredient.raw_text,
                is_optional=ingredient.is_optional,
                sort_order=ingredient.sort_order,
            )
            for ingredient in extraction.ingredients
        ],
        steps=[
            StepTextDraft(
                step_no=step.step_no,
                instruction=step.instruction,
                source_image_url=step.source_image_url,
                tip=step.tip,
                sort_order=step.sort_order,
            )
            for step in extraction.steps
        ],
        tips=tips,
    )


def _build_agent(model_name: str, timeout_seconds: float) -> Agent:
    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
    )
    return Agent(
        model,
        output_type=RecipeRewriteOutput,
        system_prompt=_SYSTEM_PROMPT,
        model_settings={"timeout": timeout_seconds},
    )


def _extraction_prompt(extraction: RecipeSourceExtraction) -> str:
    tips = [
        label.label_value
        for label in extraction.labels
        if label.label_type == "TIP" and label.label_value
    ]
    return RecipeRewriteInput(
        title=extraction.title,
        summary=extraction.summary,
        description=extraction.description,
        ingredients=[
            IngredientRewriteInput(
                index=index,
                group_name=ingredient.group_name,
                name=ingredient.name,
                amount_text=ingredient.amount_text,
                note=ingredient.note,
                raw_text=ingredient.raw_text,
                is_optional=bool(ingredient.is_optional),
            )
            for index, ingredient in enumerate(extraction.ingredients)
        ],
        steps=[
            StepRewriteInput(
                index=index,
                step_no=step.step_no,
                instruction=step.instruction,
                tip=step.tip,
            )
            for index, step in enumerate(extraction.steps)
        ],
        tips=tips,
    ).model_dump_json(indent=2)


class IngredientRewriteInput(BaseModel):
    index: int
    group_name: str | None = None
    name: str
    amount_text: str | None = None
    note: str | None = None
    raw_text: str | None = None
    is_optional: bool


class StepRewriteInput(BaseModel):
    index: int
    step_no: int
    instruction: str
    tip: str | None = None


class RecipeRewriteInput(BaseModel):
    title: str
    summary: str | None = None
    description: str | None = None
    ingredients: list[IngredientRewriteInput]
    steps: list[StepRewriteInput]
    tips: list[str] = []


def _draft_from_rewrite_output(
    original: RecipeTextDraft,
    output: RecipeRewriteOutput,
) -> RecipeTextDraft:
    steps = output.steps
    if len(steps) != len(original.steps):
        raise RecipeTextRewriteError(
            "AI rewrite step count mismatch "
            f"(expected={len(original.steps)}, got={len(steps)})"
        )

    return RecipeTextDraft(
        title=output.title,
        summary=output.summary,
        description=output.description,
        ingredients=original.ingredients,
        steps=[
            _step_from_payload(original.steps[index], item)
            for index, item in enumerate(steps)
        ],
        tips=[tip.strip() for tip in output.tips if tip and tip.strip()],
    )


def _step_from_payload(
    original: StepTextDraft,
    item: StepRewriteOutput,
) -> StepTextDraft:
    return StepTextDraft(
        step_no=original.step_no,
        instruction=_clean_required_text(item.instruction, "step.instruction"),
        source_image_url=original.source_image_url,
        tip=_clean_optional_text(item.tip),
        sort_order=original.sort_order,
    )


def _clean_required_text(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise RecipeTextRewriteError(f"AI rewrite field is required: {field}")
    return text


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


_SYSTEM_PROMPT = """
너는 Naengo 레시피 편집자다.

목표:
- 외부 레시피에서 추출된 텍스트를 Naengo 서비스의 일관된 문체로 새로 작성한다.
- 원문 문장을 그대로 복사하지 않는다.
- 의미는 유지하되 문장 구조, 어휘, 설명 순서를 새로 구성한다.
- 제목, 요약, 설명, 재료 표시 문구, 조리 순서, 팁을 모두 재작성한다.
- 재료명, 분량, 조리 순서, 조리 시간, 도구, 온도 같은 사실 정보는 바꾸지 않는다.
- 원문 고유 표현, 출처 말투, 홍보 문구, 이모지, 과장된 감탄사는 사용하지 않는다.
- 원문과 8단어 이상 연속으로 같은 표현이 나오지 않게 한다.

Naengo 문체:
- 사용자가 냉장고 속 재료로 바로 따라 할 수 있게 실용적이고 차분하게 쓴다.
- 과장된 표현보다 맛, 식감, 조리 포인트를 구체적으로 말한다.
- 제목은 짧고 검색하기 쉬운 명사형으로 쓴다.
  예: "김치 두부찌개", "버섯 간장볶음"
- summary는 한 문장으로, 핵심 재료와 결과물을 담는다.
- description은 2~4문장으로, 어떤 상황에 좋은지와 맛의 방향을 설명한다.
- 조리 순서는 한 단계에 한 행동 중심으로 쓴다.
- 단계 instruction은 "~합니다" 체를 기본으로 한다.
- tip은 실패를 줄이는 작은 조언만 적고, 없으면 null로 둔다.
- tips(레시피 전체 팁 목록)는 각 항목을 실용적인 조언으로 재작성한다.
  홍보 문구나 과장 표현은 제거하고, 의미 없는 팁은 빈 배열로 처리한다.
  입력 팁이 없으면 빈 배열로 반환한다.
- "초간단", "대박", "무조건", "역대급", "꿀맛" 같은 홍보성 표현은 쓰지 않는다.
- 이모지, 감탄사, 유튜브식 말투, 개인 블로그식 사담은 쓰지 않는다.

구조 보존:
- ingredients는 입력과 같은 개수, 같은 순서로 반환한다.
- steps는 입력과 같은 개수, 같은 순서로 반환한다.
- 재료를 합치거나 나누지 않는다.
- 조리 단계를 합치거나 나누지 않는다.
- 재료 분량, 단위, 선택 여부는 재료 파싱 단계의 값을 그대로 유지한다.
- 입력에 없는 핵심 재료, 도구, 조리법을 임의로 추가하지 않는다.
- 입력 description이 비어 있어도 title, summary, ingredients, steps를
  근거로 새 description을 작성한다.
- 입력 tip이 부족하면 억지로 만들지 말고 null로 둔다.

출력:
- 반드시 제공된 structured output schema를 따른다.
- 빈 문자열 대신 값이 없으면 null을 사용한다.
""".strip()


recipe_text_rewrite_service = AIRecipeTextRewriter()
