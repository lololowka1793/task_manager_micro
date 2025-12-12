from fastapi.testclient import TestClient

from services.comments.main import app, COMMENTS_DB

client = TestClient(app)


def setup_function():
    COMMENTS_DB.clear()


def test_create_and_list_comments_for_task():
    task_id = 1

    # Создаём комментарий
    resp = client.post(
        f"/tasks/{task_id}/comments",
        json={"author_id": 1, "text": "Test comment"},
    )
    assert resp.status_code == 201
    comment = resp.json()
    cid = comment["id"]
    assert comment["task_id"] == task_id
    assert comment["text"] == "Test comment"

    # Получаем список комментариев к задаче
    resp_list = client.get(f"/tasks/{task_id}/comments")
    assert resp_list.status_code == 200
    comments = resp_list.json()
    assert any(c["id"] == cid for c in comments)
