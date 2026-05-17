from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core import config


class UserProfileInputNormalizeError(Exception):
    pass


class UserProfileInputOutput(BaseModel):
    is_user_info: bool
    normalized_sentence: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class UserProfileInputResult:
    is_user_info: bool
    normalized_sentence: str | None
    reason: str | None = None


class UserProfileInputNormalizer:
    def __init__(
        self,
        agent: Agent | None = None,
        model: str = config.MODEL_NAME,
    ) -> None:
        self._agent = agent or _build_agent(model)

    def normalize(self, text: str) -> UserProfileInputResult:
        prompt = text.strip()
        if not prompt:
            return UserProfileInputResult(
                is_user_info=False,
                normalized_sentence=None,
                reason="empty input",
            )

        try:
            result = self._agent.run_sync(prompt)
        except Exception as exc:
            raise UserProfileInputNormalizeError(
                "profile input normalize failed"
            ) from exc

        output = result.output
        sentence = _clean_sentence(output.normalized_sentence)
        if not output.is_user_info or sentence is None:
            return UserProfileInputResult(
                is_user_info=False,
                normalized_sentence=None,
                reason=output.reason,
            )
        return UserProfileInputResult(
            is_user_info=True,
            normalized_sentence=sentence,
            reason=output.reason,
        )


def _build_agent(model_name: str) -> Agent:
    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
    )
    return Agent(
        model,
        output_type=UserProfileInputOutput,
        system_prompt=_SYSTEM_PROMPT,
    )


def _clean_sentence(value: str | None) -> str | None:
    if value is None:
        return None
    sentence = " ".join(value.strip().split())
    return sentence or None


_SYSTEM_PROMPT = """
You decide whether a single user message should be saved as long-term user profile
information for recipe personalization.

Return structured output only.

Save only stable information about the user themself:
- allergies or ingredients they cannot eat
- disliked ingredients
- preferred ingredients, cuisines, tastes, cooking styles
- dietary restrictions
- cooking skill
- preferred cooking time
- usual serving size or household size

Do not save:
- temporary requests such as "today", "this time", "right now"
- recipe recommendation requests without stable preference information
- information about another person unless the user clearly says it is their own profile
- jokes, hypotheticals, questions, commands, or unrelated text
- medical claims beyond the user's own explicit dietary/allergy preference

When saving, rewrite to exactly one concise Korean sentence.
Keep the user's meaning. Do not add facts that are not present.
Examples:
- "나 새우 알러지 있어" -> "새우 알레르기가 있어요."
- "매운 거 좋아함" -> "매운 음식을 좋아해요."
- "오늘은 닭고기 빼줘" -> not user info, temporary request.
- "엄마가 땅콩 못 먹어" -> not user info, another person.
""".strip()


user_profile_input_normalizer = UserProfileInputNormalizer()
