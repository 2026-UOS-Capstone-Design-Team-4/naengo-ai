from types import SimpleNamespace

from app.services.conversation_memory_service import ConversationMemoryBuilder


class FakeChatService:
    def load_recent_recipe_refs(self, room_id, limit=5):
        return [10, 20, 30]


class FakeQuery:
    def __init__(self, profile):
        self.profile = profile

    def filter_by(self, user_id):
        return self

    def first(self):
        return self.profile


class FakeDb:
    def __init__(self, profile):
        self.profile = profile

    def query(self, model):
        return FakeQuery(self.profile)


def test_build_memory_from_recent_refs_and_profile():
    profile = SimpleNamespace(
        allergies=["새우"],
        dietary_restrictions=["저탄수화물"],
        preferred_ingredients=["두부"],
        disliked_ingredients=["고수"],
        preferred_categories=["한식"],
        taste_keywords=["담백함"],
        cooking_skill="easy",
        preferred_cooking_time_minutes=15,
        serving_size=2,
    )

    memory = ConversationMemoryBuilder().build(
        db=FakeDb(profile),
        user_id=1,
        room_id=7,
        chat_service=FakeChatService(),
        prompt="김치랑 두부 있고 오늘은 고수 빼줘",
    )

    assert memory.short_term.recent_recipe_ids == [10, 20, 30]
    assert memory.short_term.recent_ingredients == ["김치", "두부"]
    assert memory.short_term.current_constraints == {"avoid_ingredients": ["고수"]}
    assert memory.long_term.allergies == ["새우"]
    assert memory.long_term.preferred_ingredients == ["두부"]
    assert "recent_recipe_ids" in memory.to_prompt_context()
