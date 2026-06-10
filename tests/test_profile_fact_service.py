from types import SimpleNamespace

from app.models.user import UserProfileFact
from app.services.profile_fact_service import ProfileFactInput, ProfileFactService


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.filters = {}

    def filter_by(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return [
            fact
            for fact in self.db.facts
            if all(getattr(fact, key) == value for key, value in self.filters.items())
        ]

    def first(self):
        values = self.all()
        return values[0] if values else None


class FakeDb:
    def __init__(self):
        self.facts = []
        self.next_id = 1

    def query(self, model):
        assert model is UserProfileFact
        return FakeQuery(self, model)

    def add(self, fact):
        fact.fact_id = self.next_id
        self.next_id += 1
        self.facts.append(fact)

    def delete(self, fact):
        self.facts.remove(fact)

    def flush(self):
        return None


def test_profile_facts_rebuild_and_remove_projection():
    db = FakeDb()
    profile = SimpleNamespace(
        user_id=1,
        allergies=[],
        dietary_restrictions=[],
        preferred_ingredients=[],
        disliked_ingredients=[],
        preferred_categories=[],
        taste_keywords=[],
        cooking_skill=None,
        preferred_cooking_time_minutes=None,
        serving_size=None,
    )
    service = ProfileFactService(db)

    service.add_facts(
        profile,
        [
            ProfileFactInput("dietary_restrictions", "저탄수화물"),
            ProfileFactInput("taste_keywords", "칼칼"),
        ],
        source_type="USER_INPUT",
        source_text="저탄수 식단을 하고 칼칼한 맛을 좋아해요.",
        source_key="input:1",
    )

    assert profile.dietary_restrictions == ["low_carb"]
    assert profile.taste_keywords == ["spicy"]

    service.delete_source(
        profile,
        source_type="USER_INPUT",
        source_text="저탄수 식단을 하고 칼칼한 맛을 좋아해요.",
        source_key="input:1",
    )

    assert profile.dietary_restrictions == []
    assert profile.taste_keywords == []


def test_profile_fact_delete_removes_one_duplicate_source_at_a_time():
    db = FakeDb()
    profile = SimpleNamespace(
        user_id=1,
        allergies=[],
        dietary_restrictions=[],
        preferred_ingredients=[],
        disliked_ingredients=[],
        preferred_categories=[],
        taste_keywords=[],
        cooking_skill=None,
        preferred_cooking_time_minutes=None,
        serving_size=None,
    )
    service = ProfileFactService(db)
    text = "매운 음식을 좋아해요."
    fact = ProfileFactInput("taste_keywords", "매운맛")

    service.add_facts(
        profile,
        [fact],
        source_type="USER_INPUT",
        source_text=text,
        source_key="input:1",
    )
    service.add_facts(
        profile,
        [fact],
        source_type="USER_INPUT",
        source_text=text,
        source_key="input:2",
    )

    service.delete_source(profile, source_type="USER_INPUT", source_text=text)
    assert profile.taste_keywords == ["spicy"]

    service.delete_source(profile, source_type="USER_INPUT", source_text=text)
    assert profile.taste_keywords == []
