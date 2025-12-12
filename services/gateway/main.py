from typing import Any, Dict, Optional

import os
import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


app = FastAPI(title="Gateway Service")

# ---------- Адреса всех сервисов ----------

# При запуске вне Docker берём localhost, при запуске в docker-compose — адреса из ENV
SERVICES: Dict[str, str] = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
    "users": os.getenv("USERS_SERVICE_URL", "http://localhost:8002"),
    "projects": os.getenv("PROJECTS_SERVICE_URL", "http://localhost:8003"),
    "tasks": os.getenv("TASKS_SERVICE_URL", "http://localhost:8004"),
    "comments": os.getenv("COMMENTS_SERVICE_URL", "http://localhost:8005"),
    "notifications": os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8006"),
}

# ---------- Настройка "безопасности" ----------

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_username(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Берёт заголовок Authorization: Bearer <token>,
    проверяет формат токена и достаёт username.

    Ожидаемый формат токена: token_for_<username>
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        # Нет заголовка или не Bearer
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    prefix = "token_for_"

    if not token.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = token[len(prefix):]
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token (empty username)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username


# ---------- Вспомогательные функции ----------

async def safe_get(url: str) -> Optional[Any]:
    """
    Делает HTTP GET запрос с таймаутом.

    Если запрос успешен (2xx) — возвращает JSON-ответ.
    Если произошла ошибка (сетевая, таймаут, 4xx/5xx) — возвращает None.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        print(f"[GATEWAY] Error calling {url}: {exc}")
        return None


async def proxy_post(url: str, payload: Dict[str, Any]) -> Any:
    """
    Проксирование POST-запроса.
    Если целевой сервис вернул ошибку — пробрасываем её наружу.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            # Пытаемся вернуть JSON, если он есть
            try:
                return response.json()
            except Exception:
                return {"status": "ok"}
    except httpx.HTTPStatusError as exc:
        # Пробрасываем код и текст ошибки сервиса
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error calling {url}: {exc}",
        )


# ---------- Эндпоинт /health для gateway (без авторизации) ----------

@app.get("/health")
async def gateway_health() -> Dict[str, str]:
    """
    Проверяет /health всех сервисов и возвращает их статусы.
    Если сервис недоступен или вернул ошибку — статус 'unavailable'.
    """
    statuses: Dict[str, str] = {"gateway": "ok"}

    for name, base_url in SERVICES.items():
        health_url = f"{base_url}/health"
        data = await safe_get(health_url)
        statuses[name] = "ok" if data is not None else "unavailable"

    return statuses


# ---------- Защищённый эндпоинт /summary ----------

@app.get("/summary")
async def summary(
    current_username: str = Depends(get_current_username),
) -> Dict[str, Any]:
    """
    Собирает сводную информацию по основным сущностям:
    - количество пользователей
    - количество проектов
    - количество задач

    Доступен только при наличии корректного Bearer-токена.
    """
    result: Dict[str, Any] = {
        "current_user": current_username,
        "users_count": None,
        "projects_count": None,
        "tasks_count": None,
        "users_error": None,
        "projects_error": None,
        "tasks_error": None,
    }

    # ----- Users -----
    users_data = await safe_get(f"{SERVICES['users']}/users")
    if users_data is None:
        result["users_error"] = "users_service_unavailable"
    else:
        result["users_count"] = len(users_data)

    # ----- Projects -----
    projects_data = await safe_get(f"{SERVICES['projects']}/projects")
    if projects_data is None:
        result["projects_error"] = "projects_service_unavailable"
    else:
        result["projects_count"] = len(projects_data)

    # ----- Tasks -----
    tasks_data = await safe_get(f"{SERVICES['tasks']}/tasks")
    if tasks_data is None:
        result["tasks_error"] = "tasks_service_unavailable"
    else:
        result["tasks_count"] = len(tasks_data)

    return result


# ---------- Дополнительный эндпоинт /me ----------

@app.get("/me")
async def me(
    current_username: str = Depends(get_current_username),
) -> Any:
    """
    Возвращает профиль текущего пользователя по username из токена.
    """
    users_data = await safe_get(f"{SERVICES['users']}/users")

    if users_data is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Users service unavailable",
        )

    for user in users_data:
        if user.get("username") == current_username:
            return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User '{current_username}' not found in users service",
    )


# ---------- Прокси-эндпоинты для создания сущностей ----------

@app.post("/users")
async def create_user_via_gateway(
    payload: Dict[str, Any],
    current_username: str = Depends(get_current_username),
):
    """
    Создать пользователя через gateway (проксируем в users-сервис).
    """
    url = f"{SERVICES['users']}/users"
    return await proxy_post(url, payload)


@app.post("/projects")
async def create_project_via_gateway(
    payload: Dict[str, Any],
    current_username: str = Depends(get_current_username),
):
    """
    Создать проект через gateway (проксируем в projects-сервис).
    """
    url = f"{SERVICES['projects']}/projects"
    return await proxy_post(url, payload)


@app.post("/tasks")
async def create_task_via_gateway(
    payload: Dict[str, Any],
    current_username: str = Depends(get_current_username),
):
    """
    Создать задачу через gateway (проксируем в tasks-сервис).
    """
    url = f"{SERVICES['tasks']}/tasks"
    return await proxy_post(url, payload)


@app.post("/tasks/{task_id}/comments")
async def create_comment_via_gateway(
    task_id: int,
    payload: Dict[str, Any],
    current_username: str = Depends(get_current_username),
):
    """
    Создать комментарий к задаче через gateway (проксируем в comments-сервис).
    """
    url = f"{SERVICES['comments']}/tasks/{task_id}/comments"
    return await proxy_post(url, payload)
