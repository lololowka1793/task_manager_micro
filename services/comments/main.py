from typing import List

import os
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel


# ---------- Pydantic-модели ----------

class CommentBase(BaseModel):
    author_id: int
    text: str


class Comment(CommentBase):
    id: int
    task_id: int


class CommentCreate(CommentBase):
    """Модель для создания комментария (без id и task_id)."""
    pass


# ---------- "База данных" в памяти ----------

COMMENTS_DB: List[Comment] = [
    Comment(id=1, task_id=1, author_id=1, text="Первый комментарий к задаче 1"),
    Comment(id=2, task_id=2, author_id=2, text="Обсуждение задачи 2"),
]


# ---------- Настройки уведомлений ----------

NOTIFICATIONS_BASE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8006")


def send_notification(user_id: int, message: str) -> None:
    """
    Отправка уведомления в notifications-сервис.

    Все ошибки глушим, чтобы создание комментария не ломалось.
    """
    if user_id is None:
        return

    payload = {"user_id": user_id, "message": message}
    url = f"{NOTIFICATIONS_BASE_URL}/notify"
    try:
        response = httpx.post(url, json=payload, timeout=2.0)
        response.raise_for_status()
        print(f"[COMMENTS] Notification sent to user {user_id}")
    except Exception as exc:
        print(f"[COMMENTS] Failed to send notification: {exc}")


# ---------- Приложение FastAPI ----------

app = FastAPI(title="Comments Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "comments"}


# ---------- Эндпоинты для работы с комментариями ----------

@app.get("/tasks/{task_id}/comments", response_model=List[Comment])
async def list_comments_for_task(task_id: int):
    """
    Вернуть список комментариев к конкретной задаче.
    """
    return [comment for comment in COMMENTS_DB if comment.task_id == task_id]


@app.post("/tasks/{task_id}/comments", response_model=Comment, status_code=201)
async def create_comment_for_task(
    task_id: int,
    comment_in: CommentCreate,
    background_tasks: BackgroundTasks,
):
    """
    Создать новый комментарий к задаче с данным task_id.
    id генерируется как max_id + 1.

    После создания комментария отправляем фоновое уведомление автору.
    (Для простоты: уведомляем того, кто написал комментарий.)
    """
    if COMMENTS_DB:
        max_id = max(comment.id for comment in COMMENTS_DB)
    else:
        max_id = 0

    new_comment = Comment(
        id=max_id + 1,
        task_id=task_id,
        author_id=comment_in.author_id,
        text=comment_in.text,
    )
    COMMENTS_DB.append(new_comment)

    # фоновое уведомление автору комментария
    msg = f"Ваш комментарий добавлен к задаче {task_id}"
    background_tasks.add_task(send_notification, new_comment.author_id, msg)

    return new_comment
