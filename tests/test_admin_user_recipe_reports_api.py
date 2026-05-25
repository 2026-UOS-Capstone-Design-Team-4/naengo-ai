from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1 import api as api_module
from app.api.v1.endpoints.admin import user_recipe_reports as endpoint_module
from app.main import app
from app.models.recipe import UserRecipeReport
from app.services.user_recipe_report_service import (
    UserRecipeReportInvalidCursorError,
    _build_report_cursor,
)

client = TestClient(app)


def _report(**overrides) -> UserRecipeReport:
    values = {
        "report_id": 11,
        "user_recipe_id": 22,
        "reporter_user_id": 7,
        "recipe_owner_user_id": 8,
        "reason": "INAPPROPRIATE",
        "description": "부적절한 표현이 포함되어 있어요",
        "status": "PENDING",
        "review_note": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": datetime(2026, 5, 25, tzinfo=UTC),
        "updated_at": datetime(2026, 5, 25, tzinfo=UTC),
    }
    values.update(overrides)
    return UserRecipeReport(**values)


class FakeUserRecipeReportService:
    def __init__(self, _db):
        self.report = _report()

    def get_admin_reports(self, **kwargs):
        assert kwargs == {
            "status": "PENDING",
            "user_recipe_id": 22,
            "reporter_user_id": 7,
            "recipe_owner_user_id": 8,
            "cursor": _build_report_cursor(20),
            "limit": 1,
        }
        return [self.report], _build_report_cursor(11)

    def get_admin_report(self, report_id):
        if report_id == self.report.report_id:
            return self.report
        return None

    def update_admin_report(self, report_id, body, reviewer_user_id):
        if report_id != self.report.report_id:
            return None
        self.report.status = body.status
        self.report.review_note = body.review_note
        self.report.reviewed_by = reviewer_user_id
        self.report.reviewed_at = datetime(2026, 5, 26, tzinfo=UTC)
        return self.report


class FakeInvalidCursorService(FakeUserRecipeReportService):
    def get_admin_reports(self, **kwargs):
        raise UserRecipeReportInvalidCursorError


def _override_get_db():
    yield object()


def _override_require_admin():
    return object()


def _override_get_current_user():
    return SimpleNamespace(user_id=1, role="ADMIN")


def setup_function():
    app.dependency_overrides[endpoint_module.get_db] = _override_get_db
    app.dependency_overrides[api_module.require_admin] = _override_require_admin
    app.dependency_overrides[endpoint_module.get_current_user] = (
        _override_get_current_user
    )


def teardown_function():
    app.dependency_overrides.clear()


def test_admin_can_list_user_recipe_reports(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeUserRecipeReportService,
    )

    response = client.get(
        "/api/v1/admin/user-recipe-reports",
        params={
            "status": "PENDING",
            "user_recipe_id": 22,
            "reporter_user_id": 7,
            "recipe_owner_user_id": 8,
            "cursor": _build_report_cursor(20),
            "limit": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] == _build_report_cursor(11)
    assert body["has_next"] is True
    assert body["items"][0]["report_id"] == 11
    assert body["items"][0]["reason"] == "INAPPROPRIATE"


def test_admin_report_list_returns_400_for_invalid_cursor(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeInvalidCursorService,
    )

    response = client.get("/api/v1/admin/user-recipe-reports?cursor=bad")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_admin_can_get_user_recipe_report(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeUserRecipeReportService,
    )

    response = client.get("/api/v1/admin/user-recipe-reports/11")

    assert response.status_code == 200
    assert response.json()["report_id"] == 11


def test_admin_user_recipe_report_returns_404(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeUserRecipeReportService,
    )

    response = client.get("/api/v1/admin/user-recipe-reports/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_RECIPE_REPORT_NOT_FOUND"


def test_admin_can_update_user_recipe_report(monkeypatch):
    monkeypatch.setattr(
        endpoint_module,
        "UserRecipeReportService",
        FakeUserRecipeReportService,
    )

    response = client.patch(
        "/api/v1/admin/user-recipe-reports/11",
        json={
            "status": "RESOLVED",
            "review_note": "검토 완료",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RESOLVED"
    assert body["review_note"] == "검토 완료"
    assert body["reviewed_by"] == 1
