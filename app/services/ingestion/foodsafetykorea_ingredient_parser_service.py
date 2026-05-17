import logging
from decimal import Decimal, InvalidOperation
from typing import Protocol

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core import config
from app.services.ingestion.ingredient_amount_note_service import (
    move_amount_parentheses_to_note,
)

logger = logging.getLogger(__name__)


class FoodsafetyKoreaIngredientParseError(Exception):
    pass


class FoodsafetyKoreaIngredient(BaseModel):
    group_name: str | None = None
    name: str
    normalized_name: str | None = None
    amount_text: str | None = None
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None
    raw_text: str | None = None
    is_optional: bool = False


class FoodsafetyKoreaIngredientParseOutput(BaseModel):
    ingredients: list[FoodsafetyKoreaIngredient]


class FoodsafetyKoreaIngredientParser(Protocol):
    def parse(
        self, title: str, raw_ingredients: str
    ) -> list[FoodsafetyKoreaIngredient]:
        pass


class AIFoodsafetyKoreaIngredientParser:
    def __init__(
        self,
        agent: Agent | None = None,
        model: str = config.MODEL_NAME,
    ) -> None:
        self._agent = agent or _build_agent(model)

    def parse(
        self, title: str, raw_ingredients: str
    ) -> list[FoodsafetyKoreaIngredient]:
        prompt = _ingredient_prompt(title, raw_ingredients)
        try:
            result = self._agent.run_sync(prompt)
        except Exception as exc:
            raise FoodsafetyKoreaIngredientParseError(
                "ingredient parse failed"
            ) from exc

        ingredients = result.output.ingredients
        if not ingredients:
            raise FoodsafetyKoreaIngredientParseError(
                "ingredient parse returned empty list"
            )
        normalized = []
        for item in ingredients:
            amount_note = move_amount_parentheses_to_note(
                _clean_optional_text(item.amount_text),
                _clean_optional_text(item.note),
            )
            normalized.append(
                FoodsafetyKoreaIngredient(
                    group_name=_clean_optional_text(item.group_name),
                    name=_clean_required_text(item.name, "ingredient.name"),
                    normalized_name=(
                        _clean_optional_text(item.normalized_name)
                        or _clean_required_text(item.name, "ingredient.name")
                    ),
                    amount_text=amount_note.amount_text,
                    quantity=_clean_quantity(item.quantity),
                    unit=_clean_optional_text(item.unit),
                    note=amount_note.note,
                    raw_text=_clean_optional_text(item.raw_text),
                    is_optional=bool(item.is_optional),
                )
            )
        return normalized


def _build_agent(model_name: str) -> Agent:
    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
    )
    return Agent(
        model,
        output_type=FoodsafetyKoreaIngredientParseOutput,
        system_prompt=_SYSTEM_PROMPT,
    )


def _ingredient_prompt(title: str, raw_ingredients: str) -> str:
    return f"[레시피 제목]\n{title}\n\n[원본 재료 문자열]\n{raw_ingredients}"


def _clean_required_text(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise FoodsafetyKoreaIngredientParseError(f"field is required: {field}")
    return text


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _clean_quantity(value: str | None) -> str | None:
    text = _clean_optional_text(value)
    if text is None:
        return None
    try:
        return str(Decimal(text))
    except InvalidOperation as exc:
        raise FoodsafetyKoreaIngredientParseError(
            f"quantity must be a decimal string: {text}"
        ) from exc


_SYSTEM_PROMPT = """
너는 공공데이터 레시피의 재료 문자열을 Naengo ingredient schema로 파싱한다.

목표:
- 원본 재료 문자열에서 실제 재료만 추출한다.
- "주재료", "부재료", "양념", "고명", "소스", "반죽재료" 같은 구분은
  group_name으로 옮긴다.
- 구분 제목 자체를 재료로 만들지 않는다.
- "[", "]", "•", ":", ">" 같은 장식 문자는 제거한다.
- 재료명에는 분량, 괄호, 조리 상태 설명을 섞지 않는다.
- 분량은 amount_text로 분리한다.
- 가능한 경우 quantity와 unit도 함께 추출한다.
- 손질 상태, 색상, 익은 정도, 선택 여부는 note로 분리한다.
- raw_text는 name, amount_text, note를 바탕으로 사용자가 보기 좋은 한 줄로 쓴다.

분량 표기:
- amount_text는 수량과 단위를 Naengo 표기로 일관되게 정리한다.
- 원문의 실제 수량, 단위, 선택 여부는 바꾸지 않는다.
- 숫자와 단위는 붙여 쓴다.
  예: "200 g" -> "200g", "2 개" -> "2개", "10 ml" -> "10ml"
- quantity는 숫자만 문자열로 넣는다. 예: "200g" -> quantity "200"
- unit은 단위만 넣는다. 예: "200g" -> unit "g", "1.5T" -> unit "T"
- quantity가 분수면 소수로 환산한다. 예: "1/2개" -> quantity "0.5", unit "개"
- "1과 1/2개"는 quantity "1.5", unit "개"로 둔다.
- 무게와 부피 단위는 `g`, `kg`, `ml`, `L` 표기를 우선한다.
- "큰술", "큰 술", "큰스푼", "스푼", "Ts", "TS", "tbsp"는 "T"로 통일한다.
- "작은술", "작은 술", "작은스푼", "ts", "tsp"는 "t"로 통일한다.
- 스푼 단위도 숫자와 붙여 쓴다. 예: "1.5Ts" -> "1.5T"
- "컵 분량", "cup"은 가능한 경우 "컵"으로 통일한다.
- 개수 단위는 `개`, `장`, `마리`, `쪽`, `단`, `팩`처럼 한국어 단위를 쓴다.
- 파, 대파, 쪽파, 실파처럼 파 계열 재료의 "뿌리" 단위는 "대"로 통일한다.
- "½개"는 "1/2개", "1½개"는 "1과 1/2개"처럼 일반 표기로 바꾼다.
- 괄호 안 보조 분량이나 설명은 amount_text에 붙이지 않고 note에 둔다.
  예: "50 g (1개)" -> amount_text "50g", note "1개"
- "3개 분량"처럼 불필요한 "분량"은 제거한다.
- "약간", "조금", "소량"은 의미가 같으면 "약간"으로 정리한다.
- "적당히", "적당량"은 재료 분량일 때 "적당량"으로 정리한다.
- "기호에 따라", "선택"처럼 선택 재료를 뜻하는 말은 note에 두고,
  amount_text에는 실제 분량만 둔다.
- 색상, 손질 상태, 익은 정도는 분량이 아니므로 note에 둔다.
  예: "노란색 2개" -> amount_text "2개", note "노란색"
- 단위가 명백한 오타로 보이는 경우에만 문맥에 맞게 고친다.
  예: 액체 재료의 "30m"는 "30ml"로 정리할 수 있다.
- 분량을 확정할 수 없으면 amount_text, quantity, unit은 null로 둔다.

예시:
- "간장 1큰술" -> amount_text "1T", quantity "1", unit "T"
- "고춧가루 1/2스푼" -> amount_text "1/2T", quantity "0.5", unit "T"
- "대파 1/2뿌리" -> amount_text "1/2대", quantity "0.5", unit "대"
- "파 1뿌리" -> amount_text "1대", quantity "1", unit "대"

출력:
- 반드시 제공된 structured output schema를 따른다.
- ingredients는 원본에 나타난 조리상 의미 있는 재료 순서를 유지한다.
- 빈 문자열 대신 값이 없으면 null을 사용한다.
""".strip()


foodsafetykorea_ingredient_parser = AIFoodsafetyKoreaIngredientParser()
