from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes as recipes_endpoint
from app.main import app

client = TestClient(app)


def test_not_found_uses_standard_error_shape():
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Not Found",
            "details": {},
        }
    }


def test_validation_error_uses_standard_error_shape():
    app.dependency_overrides[recipes_endpoint.get_current_user_id] = lambda: 1
    try:
        response = client.get("/api/v1/recipes", params={"limit": 0})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"]["fields"][0]["name"] == "query.limit"
