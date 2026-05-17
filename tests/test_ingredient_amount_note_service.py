from app.services.ingestion.ingredient_amount_note_service import (
    move_amount_parentheses_to_note,
)


def test_moves_parenthesized_amount_hint_to_note():
    split = move_amount_parentheses_to_note("75g(3/4모)", None)

    assert split.amount_text == "75g"
    assert split.note == "3/4모"


def test_preserves_existing_note_without_duplicates():
    split = move_amount_parentheses_to_note("20g(5마리)", "5마리")

    assert split.amount_text == "20g"
    assert split.note == "5마리"


def test_supports_fullwidth_parentheses_and_multiple_notes():
    split = move_amount_parentheses_to_note("1팩（100g）(냉동)", "선택")

    assert split.amount_text == "1팩"
    assert split.note == "선택, 100g, 냉동"
