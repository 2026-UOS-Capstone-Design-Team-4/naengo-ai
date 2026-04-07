from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root():
    """루트 엔드포인트 응답 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Naengo AI API is running"}
