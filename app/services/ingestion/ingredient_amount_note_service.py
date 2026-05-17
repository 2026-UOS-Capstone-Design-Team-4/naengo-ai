import re
from dataclasses import dataclass

_PAREN_CONTENT = re.compile(r"[\(（]([^\)）]+)[\)）]")
_PAREN_BLOCK = re.compile(r"\s*[\(（][^\)）]+[\)）]\s*")


@dataclass(frozen=True)
class AmountNoteSplit:
    amount_text: str | None
    note: str | None


def move_amount_parentheses_to_note(
    amount_text: str | None,
    note: str | None = None,
) -> AmountNoteSplit:
    """Move parenthesized amount hints from amount_text into note."""
    if not amount_text:
        return AmountNoteSplit(amount_text=None, note=_clean_text(note))

    extracted_notes = [
        item.strip() for item in _PAREN_CONTENT.findall(amount_text) if item.strip()
    ]
    clean_amount = _PAREN_BLOCK.sub("", amount_text).strip() or None
    clean_note = _join_notes(_clean_text(note), extracted_notes)
    return AmountNoteSplit(amount_text=clean_amount, note=clean_note)


def _join_notes(existing: str | None, additions: list[str]) -> str | None:
    notes = []
    seen = set()
    for item in [existing, *additions]:
        if not item:
            continue
        for part in (part.strip() for part in item.split(",")):
            if part and part not in seen:
                notes.append(part)
                seen.add(part)
    return ", ".join(notes) if notes else None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
