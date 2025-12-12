from fastapi.testclient import TestClient

from services.auth.main import app

client = TestClient(app)


def test_auth_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "auth"


def test_login_returns_token_for_username():
    resp = client.post(
        "/login",
        json={"username": "alice", "password": "anything"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "token_for_alice"
    assert data["token_type"] == "bearer"
