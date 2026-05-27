from types import SimpleNamespace

from app.services.conversation_state_service import ConversationStateResolver


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


def test_resolve_wraps_memory_with_state_hints():
    profile = SimpleNamespace(
        allergies=["새우"],
        dietary_restrictions=[],
        preferred_ingredients=["두부"],
        disliked_ingredients=["고수"],
        preferred_categories=[],
        taste_keywords=[],
        cooking_skill="easy",
        preferred_cooking_time_minutes=15,
        serving_size=2,
    )

    state = ConversationStateResolver().resolve(
        db=FakeDb(profile),
        user_id=1,
        room_id=7,
        chat_service=FakeChatService(),
        prompt="그건 별로고 오늘은 고수 빼줘",
    )

    assert state.memory.short_term.recent_recipe_ids == [10, 20, 30]
    assert state.dialogue_phase == "CONTEXT_AVAILABLE"
    assert state.current_recipe_focus == 10
    assert state.active_constraints == {"avoid_ingredients": ["고수"]}
    assert state.last_successful_search.recipe_ids == [10, 20, 30]
    assert state.rejected_recipe_ids == [10]
    assert state.profile_snapshot["allergies"] == ["새우"]
    assert "current_recipe_focus" in state.to_prompt_context()


def test_resolve_marks_possible_clarification_reply():
    state = ConversationStateResolver().resolve(
        db=None,
        user_id=None,
        room_id=None,
        chat_service=None,
        prompt="응 두부로 해줘",
    )

    assert state.pending_clarification is None
    assert state.dialogue_phase == "NEW_REQUEST"
