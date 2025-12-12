from fastapi.testclient import TestClient

from services.tasks.main import app, TASKS_DB, TaskStatus

client = TestClient(app)


def setup_function():
    TASKS_DB.clear()


def test_create_task_and_filter_and_patch_status():
    # Создание задачи
    resp = client.post(
        "/tasks",
        json={
            "project_id": 1,
            "title": "Test Task",
            "description": "Task for tests",
            "assignee_id": 1,
        },
    )
    assert resp.status_code == 201
    task = resp.json()
    tid = task["id"]
    assert task["status"] == TaskStatus.TODO.value

    # Задачи по проекту
    resp_proj = client.get("/projects/1/tasks")
    assert resp_proj.status_code == 200
    tasks_proj = resp_proj.json()
    assert any(t["id"] == tid for t in tasks_proj)

    # Меняем статус
    resp_patch = client.patch(
        f"/tasks/{tid}",
        json={"status": TaskStatus.IN_PROGRESS.value},
    )
    assert resp_patch.status_code == 200
    updated = resp_patch.json()
    assert updated["status"] == TaskStatus.IN_PROGRESS.value
