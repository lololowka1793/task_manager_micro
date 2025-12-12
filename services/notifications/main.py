from typing import List

from fastapi import FastAPI
from pydantic import BaseModel


# ---------- Pydantic-модели ----------

class Notification(BaseModel):
    user_id: int
    message: str


# Просто для истории будем хранить отправленные уведомления в памяти
NOTIFICATIONS_LOG: List[Notification] = []


# ---------- Приложение FastAPI ----------

app = FastAPI(title="Notifications Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notifications"}


# ---------- Эндпоинты для уведомлений ----------

@app.post("/notify")
async def send_notification(notification: Notification):
    """
    Принять уведомление, вывести его в консоль и добавить в локальный лог.
    """
    print(f"[NOTIFICATION] To user {notification.user_id}: {notification.message}")
    NOTIFICATIONS_LOG.append(notification)
    return {"status": "sent"}


@app.get("/notifications", response_model=List[Notification])
async def list_notifications():
    """
    Вернуть список всех полученных уведомлений (для проверки в лабораторной).
    """
    return NOTIFICATIONS_LOG
