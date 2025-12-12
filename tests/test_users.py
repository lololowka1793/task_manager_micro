from fastapi.testclient import TestClient

from services.users.main import app, Base, engine

client = TestClient(app)


def setup_function():
    # Перед каждым тестом чистим БД (таблицу users)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_and_list_users():
    # Создаём пользователя
    resp = client.post(
        "/users",
        json={"username": "testuser", "email": "testuser@example.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] > 0
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"

    # Проверяем, что он есть в списке
    resp_list = client.get("/users")
    assert resp_list.status_code == 200
    users = resp_list.json()
    assert any(u["username"] == "testuser" for u in users)


def test_get_user_by_id():
    # сначала создаём
    resp = client.post(
        "/users",
        json={"username": "u2", "email": "u2@example.com"},
    )
    assert resp.status_code == 201
    user = resp.json()
    user_id = user["id"]

    # потом забираем по id
    resp_get = client.get(f"/users/{user_id}")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert data["id"] == user_id
    assert data["username"] == "u2"
