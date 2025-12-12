from fastapi.testclient import TestClient

from services.notifications.main import app, NOTIFICATIONS_LOG

client = TestClient(app)


def setup_function():
    NOTIFICATIONS_LOG.clear()


def test_notify_and_list_notifications():
    resp = client.post(
        "/notify",
        json={"user_id": 1, "message": "Hello from tests"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"

    resp_list = client.get("/notifications")
    assert resp_list.status_code == 200
    notifications = resp_list.json()
    assert any(
        n["user_id"] == 1 and n["message"] == "Hello from tests"
        for n in notifications
    )
