from fastapi.testclient import TestClient

import services.gateway.main as gateway_module

client = TestClient(gateway_module.app)


def test_summary_requires_auth():
    resp = client.get("/summary")
    assert resp.status_code == 401


def test_me_requires_auth():
    resp = client.get("/me")
    assert resp.status_code == 401


def test_summary_with_fake_services():
    async def fake_safe_get(url: str):
        if url.endswith("/users"):
            return [
                {"id": 1, "username": "alice", "email": "alice@example.com"}
            ]
        if url.endswith("/projects"):
            return [
                {
                    "id": 1,
                    "name": "P1",
                    "description": "",
                    "owner_id": 1,
                }
            ]
        if url.endswith("/tasks"):
            return [
                {
                    "id": 1,
                    "project_id": 1,
                    "title": "T1",
                    "description": "",
                    "status": "todo",
                    "assignee_id": 1,
                }
            ]
        return None

    # подменяем safe_get на нашу фейковую версию
    gateway_module.safe_get = fake_safe_get

    headers = {"Authorization": "Bearer token_for_alice"}
    resp = client.get("/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_user"] == "alice"
    assert data["users_count"] == 1
    assert data["projects_count"] == 1
    assert data["tasks_count"] == 1


def test_me_with_fake_user():
    async def fake_safe_get(url: str):
        # вернём только одного пользователя alice
        return [
            {"id": 1, "username": "alice", "email": "alice@example.com"}
        ]

    gateway_module.safe_get = fake_safe_get

    headers = {"Authorization": "Bearer token_for_alice"}
    resp = client.get("/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
