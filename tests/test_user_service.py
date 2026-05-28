from types import SimpleNamespace

from app.schemas.user import UserInputAppendRequest, UserInputDeleteRequest
from app.services.user_service import UserService


class FakeDb:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None


class FakeUserService(UserService):
    def __init__(self, profile):
        super().__init__(FakeDb())
        self.profile = profile

    def get_profile(self, user_id: int):
        return self.profile


class FakeWithdrawalUserService(UserService):
    def __init__(self, user):
        super().__init__(FakeDb())
        self.user = user

    def get_user(self, user_id: int):
        return self.user


def test_get_profile_response_returns_user_input_in_stored_order():
    profile = SimpleNamespace(user_input=["old", "middle", "new"])
    service = FakeUserService(profile)

    response = service.get_profile_response(user_id=1)

    assert response.user_input == ["old", "middle", "new"]


def test_append_profile_user_input_stores_at_end_and_returns_stored_order():
    profile = SimpleNamespace(user_input=["old"])
    service = FakeUserService(profile)

    response = service.append_profile_user_input(
        user_id=1,
        body=UserInputAppendRequest(text="new"),
    )

    assert profile.user_input == ["old", "new"]
    assert response.user_input == ["old", "new"]
    assert service.db.committed is True


def test_delete_profile_user_inputs_removes_requested_sentence():
    profile = SimpleNamespace(user_input=["old", "delete me", "new"])
    service = FakeUserService(profile)

    response = service.delete_profile_user_inputs(
        user_id=1,
        body=UserInputDeleteRequest(text="delete me"),
    )

    assert profile.user_input == ["old", "new"]
    assert response.user_input == ["old", "new"]
    assert service.db.committed is True


def test_delete_profile_user_inputs_removes_one_matching_sentence():
    profile = SimpleNamespace(user_input=["same", "same", "new"])
    service = FakeUserService(profile)

    response = service.delete_profile_user_inputs(
        user_id=1,
        body=UserInputDeleteRequest(text="same"),
    )

    assert profile.user_input == ["same", "new"]
    assert response.user_input == ["same", "new"]
    assert service.db.committed is True


def test_withdraw_user_deactivates_account_only():
    user = SimpleNamespace(
        is_active=True,
        is_blocked=True,
        username="naengo_user",
        password_hash="hashed",
        nickname="냉장고요리왕",
    )
    service = FakeWithdrawalUserService(user)

    result = service.withdraw_user(user_id=7)

    assert result is True
    assert user.is_active is False
    assert user.is_blocked is True
    assert user.username == "naengo_user"
    assert user.password_hash == "hashed"
    assert user.nickname == "냉장고요리왕"
    assert service.db.committed is True


def test_withdraw_user_returns_false_for_inactive_user():
    user = SimpleNamespace(is_active=False)
    service = FakeWithdrawalUserService(user)

    result = service.withdraw_user(user_id=7)

    assert result is False
    assert service.db.committed is False
