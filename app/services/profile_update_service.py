import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.orm import Session

from app.core import config
from app.models.user import UserProfile
from app.services.personalization_taxonomy import canonicalize_profile_value
from app.services.profile_fact_service import ProfileFactInput, ProfileFactService


class ProfileUpdateAction(StrEnum):
    AUTO_SAVE = "AUTO_SAVE"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    IGNORE = "IGNORE"


class ProfileUpdateOperation(StrEnum):
    ADD = "add"
    SET = "set"


@dataclass(frozen=True)
class ProfileUpdateCandidate:
    field: str
    operation: ProfileUpdateOperation
    value: str | int | float
    evidence: str
    confidence: float
    scope: str
    subject: str
    reason: str | None = None

    def to_payload(self, include_evidence: bool = False) -> dict[str, Any]:
        payload = {
            "field": self.field,
            "operation": self.operation.value,
            "value": self.value,
            "confidence": self.confidence,
        }
        if self.reason:
            payload["reason"] = self.reason
        if include_evidence:
            payload["evidence"] = self.evidence
            payload["scope"] = self.scope
            payload["subject"] = self.subject
        return payload


@dataclass(frozen=True)
class ProfileUpdateDecision:
    action: ProfileUpdateAction
    candidates: list[ProfileUpdateCandidate]
    message: str | None = None

    def to_event_payload(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "candidates": [candidate.to_payload() for candidate in self.candidates],
        }


class ProfileUpdateAIOutputCandidate(BaseModel):
    field: str
    operation: ProfileUpdateOperation = ProfileUpdateOperation.ADD
    value: str | int | float
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    scope: str
    subject: str
    reason: str | None = None


class ProfileUpdateAIOutput(BaseModel):
    action: ProfileUpdateAction = ProfileUpdateAction.IGNORE
    candidates: list[ProfileUpdateAIOutputCandidate] = []
    message: str | None = None


_ALLOWLIST_FIELDS = {
    "allergies",
    "dietary_restrictions",
    "preferred_ingredients",
    "disliked_ingredients",
    "preferred_categories",
    "taste_keywords",
    "cooking_skill",
    "preferred_cooking_time_minutes",
    "serving_size",
}


class ProfileUpdateAnalyzer:
    def __init__(self, agent: Agent | None = None) -> None:
        self._agent = agent or _build_profile_update_agent()

    async def analyze(
        self,
        message: str,
        profile: UserProfile | None = None,
    ) -> ProfileUpdateDecision:
        prompt = _profile_update_prompt(message, profile)
        result = await self._agent.run(prompt)
        return _decision_from_ai_output(result.output)


class ProfileUpdateCandidateGate:
    _PROFILE_MARKERS = (
        "알레르기",
        "알러지",
        "식이",
        "채식",
        "비건",
        "당뇨",
        "탄수화물",
        "싫어",
        "좋아",
        "선호",
        "취향",
        "요리 실력",
        "조리 시간",
        "인분",
    )
    _SELF_MARKERS = ("나는", "저는", "내가", "제가", "평소", "앞으로")
    _TEMPORARY_MARKERS = ("오늘", "이번", "지금", "당장")
    _OTHER_MARKERS = ("친구", "가족", "부모", "아이", "손님", "동료")

    def should_analyze(self, message: str) -> bool:
        text = re.sub(r"\s+", " ", str(message).strip())
        if not text or not any(marker in text for marker in self._PROFILE_MARKERS):
            return False
        if text.endswith("?"):
            return False
        if any(marker in text for marker in self._OTHER_MARKERS):
            return False
        if any(marker in text for marker in self._TEMPORARY_MARKERS):
            return False
        return (
            any(marker in text for marker in self._SELF_MARKERS)
            or bool(re.search(r"(^|\s)(나|저)(\s|$)", text))
            or bool(re.search(r"(알레르기|알러지).*(있어|있습니다|있음)", text))
            or bool(
                re.search(
                    r"(당뇨|건강).*(때문에|라서).*(줄여야|피해야|먹어야)",
                    text,
                )
            )
        )


class ProfileUpdateExtractor:
    def __init__(self, analyzer: ProfileUpdateAnalyzer | None = None) -> None:
        self._analyzer = analyzer or ProfileUpdateAnalyzer()

    async def extract(self, message: str) -> list[ProfileUpdateCandidate]:
        return (await self._analyzer.analyze(message)).candidates

    async def analyze(
        self,
        message: str,
        profile: UserProfile | None = None,
    ) -> ProfileUpdateDecision:
        return await self._analyzer.analyze(message, profile)


class ProfileUpdatePolicy:
    def decide(
        self,
        candidates: list[ProfileUpdateCandidate],
        profile: UserProfile | None,
    ) -> ProfileUpdateDecision:
        del profile
        if not candidates:
            return ProfileUpdateDecision(ProfileUpdateAction.IGNORE, [])
        return ProfileUpdateDecision(
            action=ProfileUpdateAction.REQUIRE_CONFIRMATION,
            candidates=candidates,
            message=_build_confirmation_message(candidates),
        )


class UserProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_profile(self, user_id: int) -> UserProfile:
        profile = (
            self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        )
        if profile is None:
            profile = UserProfile(user_id=user_id, user_input=[])
            self.db.add(profile)
            self.db.flush()
        return profile

    def apply_candidates(
        self, user_id: int, candidates: list[ProfileUpdateCandidate]
    ) -> UserProfile:
        profile = self.get_or_create_profile(user_id)
        facts = []
        for candidate in candidates:
            value = canonicalize_profile_value(candidate.field, candidate.value)
            facts.append(
                ProfileFactInput(
                    field=candidate.field,
                    value=value,
                    display_value=str(candidate.value),
                )
            )

        if facts and isinstance(self.db, Session):
            source_text = " | ".join(
                dict.fromkeys(candidate.evidence for candidate in candidates)
            )
            ProfileFactService(self.db).add_facts(
                profile,
                facts,
                source_type="CHAT",
                source_text=source_text,
            )
        else:
            for candidate, fact in zip(candidates, facts, strict=True):
                if candidate.operation == ProfileUpdateOperation.ADD:
                    values = _list_value(getattr(profile, candidate.field, None))
                    if fact.value not in values:
                        values.append(fact.value)
                    setattr(profile, candidate.field, values)
                elif candidate.operation == ProfileUpdateOperation.SET:
                    setattr(profile, candidate.field, fact.value)
        self.db.commit()
        self.db.refresh(profile)
        return profile


def _decision_from_ai_output(output: ProfileUpdateAIOutput) -> ProfileUpdateDecision:
    candidates = [
        ProfileUpdateCandidate(
            field=item.field,
            operation=item.operation,
            value=item.value,
            evidence=item.evidence,
            confidence=item.confidence,
            scope=item.scope,
            subject=item.subject,
            reason=item.reason,
        )
        for item in output.candidates
        if item.field in _ALLOWLIST_FIELDS
    ]
    if output.action == ProfileUpdateAction.IGNORE or not candidates:
        return ProfileUpdateDecision(ProfileUpdateAction.IGNORE, [])
    return ProfileUpdateDecision(
        action=output.action,
        candidates=candidates,
        message=output.message or _message_for_action(output.action, candidates),
    )


def _message_for_action(
    action: ProfileUpdateAction,
    candidates: list[ProfileUpdateCandidate],
) -> str:
    if action == ProfileUpdateAction.AUTO_SAVE:
        return _build_auto_save_message(candidates)
    if action == ProfileUpdateAction.REQUIRE_CONFIRMATION:
        return _build_confirmation_message(candidates)
    return ""


def _build_profile_update_agent() -> Agent:
    model = OpenAIChatModel(
        config.MODEL_NAME,
        provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
    )
    return Agent(
        model,
        output_type=ProfileUpdateAIOutput,
        system_prompt=_PROFILE_UPDATE_PROMPT,
    )


def _profile_update_prompt(message: str, profile: UserProfile | None) -> str:
    return (
        f"[Current profile]\n{_profile_context(profile)}\n\n"
        f"[User message]\n{message.strip()}"
    )


def _profile_context(profile: UserProfile | None) -> str:
    if profile is None:
        return "No saved profile."
    payload = {
        "allergies": _list_value(profile.allergies),
        "dietary_restrictions": _list_value(profile.dietary_restrictions),
        "preferred_ingredients": _list_value(profile.preferred_ingredients),
        "disliked_ingredients": _list_value(profile.disliked_ingredients),
        "preferred_categories": _list_value(profile.preferred_categories),
        "taste_keywords": _list_value(profile.taste_keywords),
        "cooking_skill": profile.cooking_skill,
        "preferred_cooking_time_minutes": profile.preferred_cooking_time_minutes,
        "serving_size": float(profile.serving_size) if profile.serving_size else None,
    }
    return str(payload)


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _build_auto_save_message(candidates: list[ProfileUpdateCandidate]) -> str:
    labels = [_format_candidate(candidate) for candidate in candidates]
    return f"{', '.join(labels)} 프로필에 저장했어요. 앞으로 추천에 반영할게요."


def _build_confirmation_message(candidates: list[ProfileUpdateCandidate]) -> str:
    labels = [_format_candidate(candidate) for candidate in candidates]
    return f"{', '.join(labels)} 프로필에 저장해둘까요?"


def _format_candidate(candidate: ProfileUpdateCandidate) -> str:
    field_labels = {
        "allergies": "알레르기",
        "dietary_restrictions": "식이 제한",
        "preferred_ingredients": "선호 재료",
        "disliked_ingredients": "제외 재료",
        "preferred_cooking_time_minutes": "선호 조리 시간",
        "serving_size": "선호 인분",
    }
    label = field_labels.get(candidate.field, candidate.field)
    value = candidate.value
    if candidate.field == "preferred_cooking_time_minutes":
        value = f"{value}분 이내"
    elif candidate.field == "serving_size":
        value = f"{value:g}인분" if isinstance(value, float) else f"{value}인분"
    return f"{label} '{value}'"


_PROFILE_UPDATE_PROMPT = """
You decide whether a user chat message should update long-term recipe
personalization profile data. Return structured output only.

Allowed fields:
- allergies
- dietary_restrictions
- preferred_ingredients
- disliked_ingredients
- preferred_categories
- taste_keywords
- cooking_skill
- preferred_cooking_time_minutes
- serving_size

Use AUTO_SAVE only when the message clearly states stable information about the
user themself and does not conflict with the current profile.

Use REQUIRE_CONFIRMATION when the information may be stable but is ambiguous,
temporary, health-related, or conflicts with the current profile.

Use IGNORE for questions, negations, hypotheticals, jokes, temporary recipe
requests, unrelated text, and information about another person.

For candidates:
- field must be one allowed field.
- operation is add for list fields and set for scalar fields.
- value must be the normalized Korean value or a number for numeric fields.
- evidence is the exact user phrase that supports the candidate.
- confidence is 0.0 to 1.0.
- subject should be self, other, or ambiguous.
- scope should be long_term, temporary, hypothetical, or unclear.
- reason should briefly explain uncertainty when action is REQUIRE_CONFIRMATION.

Examples:
- "나 새우 알러지 있어" => AUTO_SAVE allergies 새우
- "나는 계란 알레르기는 없어" => IGNORE
- "나 알레르기 있어 새우" => AUTO_SAVE allergies 새우
- "국내산 새우 알레르기 있어?" => IGNORE
- "오늘은 고수 빼줘" => IGNORE
- "당뇨 때문에 탄수화물을 줄여야 해" => REQUIRE_CONFIRMATION
- "새우 알레르기 있는 친구가 와" => IGNORE
""".strip()


profile_update_analyzer = ProfileUpdateAnalyzer()
profile_update_extractor = ProfileUpdateExtractor(profile_update_analyzer)
profile_update_candidate_gate = ProfileUpdateCandidateGate()
profile_update_policy = ProfileUpdatePolicy()
