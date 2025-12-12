from fastapi.testclient import TestClient

from services.projects.main import app, PROJECTS_DB

client = TestClient(app)


def setup_function():
    # Очищаем in-memory "базу" перед каждым тестом
    PROJECTS_DB.clear()


def test_create_and_get_project():
    resp = client.post(
        "/projects",
        json={
            "name": "Test Project",
            "description": "Project created in tests",
            "owner_id": 1,
        },
    )
    assert resp.status_code == 201
    project = resp.json()
    pid = project["id"]

    # Список
    resp_list = client.get("/projects")
    assert resp_list.status_code == 200
    projects = resp_list.json()
    assert any(p["id"] == pid for p in projects)

    # По id
    resp_get = client.get(f"/projects/{pid}")
    assert resp_get.status_code == 200
    got = resp_get.json()
    assert got["name"] == "Test Project"
