from fastapi import FastAPI
from pydantic import BaseModel


# ---------- Pydantic-модели ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Приложение FastAPI ----------

app = FastAPI(title="Auth Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}


# ---------- Эндпоинты авторизации ----------

@app.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    """
    Упрощённый логин.

    Принимает любые username и password и возвращает "фейковый" токен.
    Токен зависит только от username.
    """
    token = f"token_for_{data.username}"
    return LoginResponse(access_token=token, token_type="bearer")
