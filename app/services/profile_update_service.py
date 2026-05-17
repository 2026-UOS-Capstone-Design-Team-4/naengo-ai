import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import UserProfile


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
_AUTO_SAVE_CONFIDENCE = 0.9
_TEMPORARY_PATTERN = re.compile(
    r"(오늘|이번(?:엔|에는)?|지금(?:은)?|요즘|이번 주|당장)"
)
_OTHER_SUBJECT_PATTERN = re.compile(
    r"(친구|가족|엄마|아빠|아이|애가|손님|동료|남친|여친|아내|남편)"
)
_SELF_PATTERN = re.compile(r"(나|나는|난|저|저는|제가|내가|내|앞으로)")
_HEALTH_PATTERN = re.compile(r"(당뇨|고혈압|질병|병원|의사|치료|약|혈당|신장|간질환)")
_JOKE_OR_HYPOTHETICAL_PATTERN = re.compile(r"(만약|예를 들면|예시|농담|라고 치면)")
_TOKEN_PATTERN = r"([가-힣A-Za-z0-9]+)"


class ProfileUpdateExtractor:
    def extract(self, message: str) -> list[ProfileUpdateCandidate]:
        text = message.strip()
        subject = _detect_subject(text)
        scope = _detect_scope(text)
        candidates: list[ProfileUpdateCandidate] = []

        candidates.extend(self._extract_allergies(text, subject, scope))
        candidates.extend(self._extract_disliked_ingredients(text, subject, scope))
        candidates.extend(self._extract_preferred_ingredients(text, subject, scope))
        candidates.extend(self._extract_dietary_restrictions(text, subject, scope))
        candidates.extend(self._extract_cooking_time(text, subject, scope))
        candidates.extend(self._extract_serving_size(text, subject, scope))
        return candidates

    def _extract_allergies(
        self, text: str, subject: str, scope: str
    ) -> list[ProfileUpdateCandidate]:
        candidates = []
        patterns = [
            rf"{_TOKEN_PATTERN}\s*알레르기(?:가|는)?\s*(?:있어|있음|있습니다|있어요)",
            rf"(?:알레르기(?:가|는)?\s*){_TOKEN_PATTERN}",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                value = _normalize_food(match.group(1))
                if value:
                    candidates.append(
                        _candidate(
                            field="allergies",
                            value=value,
                            evidence=text,
                            subject=subject,
                            scope=scope,
                            confidence=0.96 if subject == "self" else 0.7,
                        )
                    )
        return _dedupe_candidates(candidates)

    def _extract_disliked_ingredients(
        self, text: str, subject: str, scope: str
    ) -> list[ProfileUpdateCandidate]:
        candidates = []
        patterns = [
            rf"{_TOKEN_PATTERN}(?:은|는|이|가)?\s*(?:싫어|싫습니다|싫어요|못\s*먹어|못\s*먹어요)",
            rf"(?:앞으로\s*)?{_TOKEN_PATTERN}(?:은|는)?\s*(?:빼줘|제외해줘|넣지\s*마)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                value = _normalize_food(match.group(1))
                if value and value not in {"오늘", "요즘", "이번"}:
                    candidates.append(
                        _candidate(
                            field="disliked_ingredients",
                            value=value,
                            evidence=text,
                            subject=subject,
                            scope=scope,
                            confidence=0.94 if subject == "self" else 0.68,
                        )
                    )
        return _dedupe_candidates(candidates)

    def _extract_preferred_ingredients(
        self, text: str, subject: str, scope: str
    ) -> list[ProfileUpdateCandidate]:
        candidates = []
        pattern = rf"{_TOKEN_PATTERN}(?:은|는|이|가)?\s*(?:좋아|좋아해|좋습니다|좋아요)"
        for match in re.finditer(pattern, text):
            value = _normalize_food(match.group(1))
            if value:
                candidates.append(
                    _candidate(
                        field="preferred_ingredients",
                        value=value,
                        evidence=text,
                        subject=subject,
                        scope=scope,
                        confidence=0.93 if subject == "self" else 0.68,
                    )
                )
        return _dedupe_candidates(candidates)

    def _extract_dietary_restrictions(
        self, text: str, subject: str, scope: str
    ) -> list[ProfileUpdateCandidate]:
        keywords = {
            "비건": "비건",
            "채식": "채식",
            "저탄수": "저탄수화물",
            "저탄고지": "저탄수화물",
            "글루텐프리": "글루텐프리",
            "무글루텐": "글루텐프리",
            "유제품 안": "유제품 제한",
        }
        candidates = []
        for raw, normalized in keywords.items():
            if raw in text:
                candidates.append(
                    _candidate(
                        field="dietary_restrictions",
                        value=normalized,
                        evidence=text,
                        subject=subject,
                        scope=scope,
                        confidence=0.92 if subject == "self" else 0.7,
                        )
                )
        if "탄수화물" in text and re.search(r"(줄|적게|낮)", text):
            candidates.append(
                _candidate(
                    field="dietary_restrictions",
                    value="저탄수화물",
                    evidence=text,
                    subject=subject,
                    scope=scope,
                    confidence=0.86,
                )
            )
        return _dedupe_candidates(candidates)

    def _extract_cooking_time(
        self, text: str, subject: str, scope: str
    ) -> list[ProfileUpdateCandidate]:
        match = re.search(r"(\d{1,3})\s*분\s*(?:안에|이내|내)", text)
        if not match:
            return []
        return [
            ProfileUpdateCandidate(
                field="preferred_cooking_time_minutes",
                operation=ProfileUpdateOperation.SET,
                value=int(match.group(1)),
                evidence=text,
                confidence=0.94 if subject == "self" else 0.7,
                scope=scope,
                subject=subject,
            )
        ]

    def _extract_serving_size(
        self, text: str, subject: str, scope: str
    ) -> list[ProfileUpdateCandidate]:
        match = re.search(r"(\d{1,2})\s*인분", text)
        if not match:
            return []
        return [
            ProfileUpdateCandidate(
                field="serving_size",
                operation=ProfileUpdateOperation.SET,
                value=float(match.group(1)),
                evidence=text,
                confidence=0.9 if subject == "self" else 0.68,
                scope=scope,
                subject=subject,
            )
        ]


class ProfileUpdatePolicy:
    def decide(
        self,
        candidates: list[ProfileUpdateCandidate],
        profile: UserProfile | None,
    ) -> ProfileUpdateDecision:
        if not candidates:
            return ProfileUpdateDecision(ProfileUpdateAction.IGNORE, [])

        auto_save = []
        confirmation = []
        for candidate in candidates:
            reason = self._confirmation_reason(candidate, profile)
            if reason is None:
                auto_save.append(candidate)
            elif reason != "ignore":
                confirmation.append(_with_reason(candidate, reason))

        if auto_save:
            return ProfileUpdateDecision(
                action=ProfileUpdateAction.AUTO_SAVE,
                candidates=auto_save,
                message=_build_auto_save_message(auto_save),
            )
        if confirmation:
            return ProfileUpdateDecision(
                action=ProfileUpdateAction.REQUIRE_CONFIRMATION,
                candidates=confirmation,
                message=_build_confirmation_message(confirmation),
            )
        return ProfileUpdateDecision(ProfileUpdateAction.IGNORE, [])

    def _confirmation_reason(
        self,
        candidate: ProfileUpdateCandidate,
        profile: UserProfile | None,
    ) -> str | None:
        if candidate.field not in _ALLOWLIST_FIELDS:
            return "ignore"
        if candidate.subject == "other":
            return "ignore"
        if candidate.scope != "long_term":
            return "일시적인 조건일 수 있어 장기 프로필 저장 전 확인이 필요함"
        if _HEALTH_PATTERN.search(candidate.evidence):
            return "건강 상태와 연결된 식단 정보라 사용자 확인이 필요함"
        if candidate.subject != "self":
            return "주어가 본인인지 명확하지 않아 확인이 필요함"
        if candidate.confidence < _AUTO_SAVE_CONFIDENCE:
            return "confidence가 자동 저장 기준보다 낮아 확인이 필요함"
        if _has_conflict(candidate, profile):
            return "기존 프로필과 충돌해 사용자 확인이 필요함"
        return None


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
        for candidate in candidates:
            if candidate.operation == ProfileUpdateOperation.ADD:
                values = _list_value(getattr(profile, candidate.field, None))
                if candidate.value not in values:
                    values.append(candidate.value)
                setattr(profile, candidate.field, values)
            elif candidate.operation == ProfileUpdateOperation.SET:
                setattr(profile, candidate.field, candidate.value)

        self.db.commit()
        self.db.refresh(profile)
        return profile


profile_update_extractor = ProfileUpdateExtractor()
profile_update_policy = ProfileUpdatePolicy()


def _candidate(
    field: str,
    value: str,
    evidence: str,
    subject: str,
    scope: str,
    confidence: float,
) -> ProfileUpdateCandidate:
    return ProfileUpdateCandidate(
        field=field,
        operation=ProfileUpdateOperation.ADD,
        value=value,
        evidence=evidence,
        confidence=confidence,
        scope=scope,
        subject=subject,
    )


def _detect_subject(text: str) -> str:
    if _OTHER_SUBJECT_PATTERN.search(text):
        return "other"
    if _SELF_PATTERN.search(text):
        return "self"
    return "ambiguous"


def _detect_scope(text: str) -> str:
    if _TEMPORARY_PATTERN.search(text):
        return "temporary"
    if _JOKE_OR_HYPOTHETICAL_PATTERN.search(text):
        return "hypothetical"
    return "long_term"


def _normalize_food(value: str) -> str:
    return value.strip(" 은는이가을를도,.;!?~")


def _dedupe_candidates(
    candidates: list[ProfileUpdateCandidate],
) -> list[ProfileUpdateCandidate]:
    seen = set()
    result = []
    for candidate in candidates:
        key = (candidate.field, candidate.operation, candidate.value)
        if key not in seen:
            result.append(candidate)
            seen.add(key)
    return result


def _with_reason(
    candidate: ProfileUpdateCandidate, reason: str
) -> ProfileUpdateCandidate:
    return ProfileUpdateCandidate(
        field=candidate.field,
        operation=candidate.operation,
        value=candidate.value,
        evidence=candidate.evidence,
        confidence=candidate.confidence,
        scope=candidate.scope,
        subject=candidate.subject,
        reason=reason,
    )


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _has_conflict(
    candidate: ProfileUpdateCandidate, profile: UserProfile | None
) -> bool:
    if profile is None:
        return False
    value = candidate.value
    if candidate.field == "preferred_ingredients":
        return value in _list_value(profile.disliked_ingredients)
    if candidate.field == "disliked_ingredients":
        return value in _list_value(profile.preferred_ingredients)
    return False


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
