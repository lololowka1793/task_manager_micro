from enum import Enum
from typing import List, Optional

import os
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel


# ---------- Статусы задач ----------

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


# ---------- Pydantic-модели ----------

class TaskBase(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    assignee_id: Optional[int] = None  # id пользователя-исполнителя


class Task(TaskBase):
    id: int


class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    assignee_id: Optional[int] = None


# ---------- "База данных" в памяти ----------

TASKS_DB: List[Task] = [
    Task(
        id=1,
        project_id=1,
        title="Настроить окружение",
        description="Установить Python, создать виртуальное окружение для проекта",
        status=TaskStatus.DONE,
        assignee_id=1,
    ),
    Task(
        id=2,
        project_id=1,
        title="Сделать Users Service",
        description="Реализовать сервис пользователей с in-memory хранением",
        status=TaskStatus.IN_PROGRESS,
        assignee_id=1,
    ),
    Task(
        id=3,
        project_id=2,
        title="Описать архитектуру",
        description="Написать файл docs/architecture.md",
        status=TaskStatus.DONE,
        assignee_id=2,
    ),
]


# ---------- Настройки уведомлений ----------

# В docker-compose NOTIFICATIONS_SERVICE_URL будет вида http://notifications:8006
NOTIFICATIONS_BASE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8006")


def send_notification(user_id: int, message: str) -> None:
    """
    Отправка уведомления в notifications-сервис.

    ВАЖНО: все ошибки глушим, чтобы создание задачи не ломалось.
    """
    if user_id is None:
        return

    payload = {"user_id": user_id, "message": message}
    url = f"{NOTIFICATIONS_BASE_URL}/notify"
    try:
        response = httpx.post(url, json=payload, timeout=2.0)
        response.raise_for_status()
        print(f"[TASKS] Notification sent to user {user_id}")
    except Exception as exc:
        # Просто логируем ошибку, но не пробрасываем её наверх.
        print(f"[TASKS] Failed to send notification: {exc}")


# ---------- Приложение FastAPI ----------

app = FastAPI(title="Tasks Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tasks"}


# ---------- Эндпоинты для работы с задачами ----------

@app.get("/tasks", response_model=List[Task])
async def list_tasks():
    """
    Вернуть список всех задач.
    """
    return TASKS_DB


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    """
    Вернуть одну задачу по id.
    Если задача не найдена — 404.
    """
    for task in TASKS_DB:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/projects/{project_id}/tasks", response_model=List[Task])
async def list_tasks_by_project(project_id: int):
    """
    Вернуть список задач только для одного проекта.
    """
    return [task for task in TASKS_DB if task.project_id == project_id]


@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(task_in: TaskCreate, background_tasks: BackgroundTasks):
    """
    Создать новую задачу.

    status по умолчанию "todo".
    id генерируется как max_id + 1.

    После создания задачи отправляем фоновое уведомление исполнителю (если assignee_id указан).
    """
    if TASKS_DB:
        max_id = max(task.id for task in TASKS_DB)
    else:
        max_id = 0

    new_task = Task(
        id=max_id + 1,
        project_id=task_in.project_id,
        title=task_in.title,
        description=task_in.description,
        status=TaskStatus.TODO,
        assignee_id=task_in.assignee_id,
    )
    TASKS_DB.append(new_task)

    # добавляем фоновую задачу по отправке уведомления
    if new_task.assignee_id is not None:
        msg = f"Вам назначена задача: {new_task.title}"
        background_tasks.add_task(send_notification, new_task.assignee_id, msg)

    return new_task


@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_update: TaskUpdate):
    """
    Обновить задачу:
    - можно изменить title, description, status, assignee_id.
    """
    for index, task in enumerate(TASKS_DB):
        if task.id == task_id:
            updated_data = task.dict()

            if task_update.title is not None:
                updated_data["title"] = task_update.title
            if task_update.description is not None:
                updated_data["description"] = task_update.description
            if task_update.status is not None:
                updated_data["status"] = task_update.status
            if task_update.assignee_id is not None:
                updated_data["assignee_id"] = task_update.assignee_id

            updated_task = Task(**updated_data)
            TASKS_DB[index] = updated_task
            return updated_task

    raise HTTPException(status_code=404, detail="Task not found")


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """
    Удалить задачу по id.

    Если задача не найдена — 404.
    """
    for index, task in enumerate(TASKS_DB):
        if task.id == task_id:
            TASKS_DB.pop(index)
            return

    raise HTTPException(status_code=404, detail="Task not found")
