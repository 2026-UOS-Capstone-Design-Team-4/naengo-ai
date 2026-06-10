import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models.user import UserProfile  # noqa: E402
from app.services.personalization_taxonomy import (  # noqa: E402
    canonicalize_profile_value,
    profile_field_is_list,
)
from app.services.profile_fact_service import (  # noqa: E402
    ProfileFactInput,
    ProfileFactService,
    profile_fact_source_key,
)
from app.services.user_profile_input_service import (  # noqa: E402
    UserProfileInputNormalizeError,
    user_profile_input_normalizer,
)

logger = logging.getLogger(__name__)

_PROFILE_FIELDS = (
    "allergies",
    "dietary_restrictions",
    "preferred_ingredients",
    "disliked_ingredients",
    "preferred_categories",
    "taste_keywords",
    "cooking_skill",
    "preferred_cooking_time_minutes",
    "serving_size",
)


@dataclass
class BackfillReport:
    profiles: int = 0
    facts: int = 0
    unresolved_inputs: list[dict] = field(default_factory=list)


def backfill(*, apply: bool, limit: int | None = None) -> BackfillReport:
    db = SessionLocal()
    report = BackfillReport()
    try:
        query = db.query(UserProfile).order_by(UserProfile.user_id)
        if limit is not None:
            query = query.limit(limit)
        for profile in query.all():
            report.profiles += 1
            facts = _structured_profile_facts(profile)
            input_facts, unresolved = _user_input_facts(profile)
            facts.extend(input_facts)
            report.facts += len(facts)
            report.unresolved_inputs.extend(unresolved)
            if not apply:
                continue
            fact_service = ProfileFactService(db)
            for source_type, source_text, source_key, fact in facts:
                fact_service.add_facts(
                    profile,
                    [fact],
                    source_type=source_type,
                    source_text=source_text,
                    source_key=source_key,
                )
        if apply:
            db.commit()
        else:
            db.rollback()
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _structured_profile_facts(profile: UserProfile) -> list[tuple]:
    facts = []
    for field_name in _PROFILE_FIELDS:
        raw_value = getattr(profile, field_name, None)
        values = raw_value if profile_field_is_list(field_name) else [raw_value]
        if not isinstance(values, list):
            values = []
        for value in values:
            if value is None or not str(value).strip():
                continue
            canonical = canonicalize_profile_value(field_name, value)
            facts.append(
                (
                    "BACKFILL",
                    f"{field_name}={value}",
                    f"structured:{field_name}:{canonical}",
                    ProfileFactInput(
                        field=field_name,
                        value=canonical,
                        display_value=str(value),
                    ),
                )
            )
    return facts


def _user_input_facts(profile: UserProfile) -> tuple[list[tuple], list[dict]]:
    facts = []
    unresolved = []
    occurrence_by_text: dict[str, int] = {}
    for text in profile.user_input or []:
        if not isinstance(text, str) or not text.strip():
            continue
        normalized_text = " ".join(text.strip().split())
        occurrence_by_text[normalized_text] = (
            occurrence_by_text.get(normalized_text, 0) + 1
        )
        occurrence = occurrence_by_text[normalized_text]
        try:
            result = user_profile_input_normalizer.normalize(normalized_text)
        except UserProfileInputNormalizeError as exc:
            unresolved.append(
                {
                    "user_id": profile.user_id,
                    "text": normalized_text,
                    "reason": str(exc),
                }
            )
            continue
        if not result.is_user_info or not result.facts:
            unresolved.append(
                {
                    "user_id": profile.user_id,
                    "text": normalized_text,
                    "reason": result.reason or "no structured facts",
                }
            )
            continue
        for item in result.facts:
            facts.append(
                (
                    "USER_INPUT",
                    normalized_text,
                    (
                        f"{profile_fact_source_key('USER_INPUT', normalized_text)}"
                        f":{occurrence}"
                    ),
                    ProfileFactInput(field=item.field, value=item.value),
                )
            )
    return facts, unresolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    report = backfill(apply=args.apply, limit=args.limit)
    logger.warning(
        "profile fact backfill apply=%s profiles=%d facts=%d unresolved=%d",
        args.apply,
        report.profiles,
        report.facts,
        len(report.unresolved_inputs),
    )
    for item in report.unresolved_inputs:
        logger.warning("unresolved profile input: %s", item)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
