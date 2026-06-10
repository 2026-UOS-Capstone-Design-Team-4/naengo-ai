from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import UserProfile, UserProfileFact
from app.services.personalization_taxonomy import (
    canonicalize_profile_value,
    profile_field_is_list,
    profile_field_is_scalar,
)


@dataclass(frozen=True)
class ProfileFactInput:
    field: str
    value: str | int | float
    display_value: str | None = None


class ProfileFactService:
    def __init__(self, db: Session):
        self.db = db

    def add_facts(
        self,
        profile: UserProfile,
        facts: list[ProfileFactInput],
        *,
        source_type: str,
        source_text: str,
        source_key: str | None = None,
    ) -> None:
        key = source_key or profile_fact_source_key(source_type, source_text)
        touched_fields: set[str] = set()
        if source_type != "BACKFILL":
            self._preserve_existing_projection(
                profile,
                {fact.field for fact in facts},
            )
        for fact in facts:
            canonical = canonicalize_profile_value(fact.field, fact.value)
            display = fact.display_value or str(fact.value)
            if not str(canonical).strip():
                continue
            existing = (
                self.db.query(UserProfileFact)
                .filter_by(
                    user_id=profile.user_id,
                    field=fact.field,
                    canonical_value=str(canonical),
                    source_type=source_type,
                    source_key=key,
                )
                .first()
            )
            if existing is None:
                self.db.add(
                    UserProfileFact(
                        user_id=profile.user_id,
                        field=fact.field,
                        canonical_value=str(canonical),
                        display_value=str(display),
                        source_type=source_type,
                        source_text=source_text,
                        source_key=key,
                    )
                )
            touched_fields.add(fact.field)
        self.db.flush()
        self.rebuild_projection(profile, touched_fields)

    def _preserve_existing_projection(
        self,
        profile: UserProfile,
        fields: set[str],
    ) -> None:
        for field in fields:
            existing_fact = (
                self.db.query(UserProfileFact)
                .filter_by(user_id=profile.user_id, field=field)
                .first()
            )
            if existing_fact is not None:
                continue
            current = getattr(profile, field, None)
            values = current if profile_field_is_list(field) else [current]
            if not isinstance(values, list):
                continue
            for value in values:
                if value is None or not str(value).strip():
                    continue
                canonical = canonicalize_profile_value(field, value)
                self.db.add(
                    UserProfileFact(
                        user_id=profile.user_id,
                        field=field,
                        canonical_value=str(canonical),
                        display_value=str(value),
                        source_type="BACKFILL",
                        source_text=f"legacy projection: {field}",
                        source_key=f"legacy:{field}:{canonical}",
                    )
                )
        self.db.flush()

    def delete_source(
        self,
        profile: UserProfile,
        *,
        source_type: str,
        source_text: str,
        source_key: str | None = None,
    ) -> None:
        filters = {
            "user_id": profile.user_id,
            "source_type": source_type,
        }
        if source_key is not None:
            filters["source_key"] = source_key
        else:
            filters["source_text"] = source_text
        facts = list(
            self.db.query(UserProfileFact)
            .filter_by(**filters)
            .order_by(UserProfileFact.fact_id)
            .all()
        )
        if source_key is None and facts:
            first_source_key = facts[0].source_key
            facts = [fact for fact in facts if fact.source_key == first_source_key]
        touched_fields = {fact.field for fact in facts}
        for fact in facts:
            self.db.delete(fact)
        self.db.flush()
        self.rebuild_projection(profile, touched_fields)

    def rebuild_projection(
        self,
        profile: UserProfile,
        fields: set[str] | None = None,
    ) -> None:
        target_fields = fields or {
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
        for field in target_fields:
            facts = (
                self.db.query(UserProfileFact)
                .filter_by(user_id=profile.user_id, field=field)
                .order_by(UserProfileFact.fact_id)
                .all()
            )
            if profile_field_is_list(field):
                values = list(
                    dict.fromkeys(fact.canonical_value for fact in facts)
                )
                setattr(profile, field, values)
            elif profile_field_is_scalar(field):
                value: Any = facts[-1].canonical_value if facts else None
                if value is not None and field == "preferred_cooking_time_minutes":
                    value = int(float(value))
                elif value is not None and field == "serving_size":
                    value = float(value)
                setattr(profile, field, value)


def profile_fact_source_key(source_type: str, source_text: str) -> str:
    payload = f"{source_type}:{' '.join(source_text.strip().split())}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
