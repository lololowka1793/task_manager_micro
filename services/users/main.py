from typing import List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session


# ---------- Настройки БД ----------

# Файл users.db будет лежать в папке services/users
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"

# connect_args нужен для SQLite, чтобы можно было использовать соединение в нескольких потоках
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------- SQLAlchemy-модель (таблица users) ----------

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)


# ---------- Pydantic-модели ----------

class UserBase(BaseModel):
    username: str
    email: EmailStr


class User(UserBase):
    id: int


class UserCreate(UserBase):
    """Модель для создания пользователя (без id)."""
    pass


# ---------- Зависимость для работы с БД ----------

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Приложение FastAPI ----------

app = FastAPI(title="Users Service")


@app.on_event("startup")
def on_startup():
    """
    При старте приложения создаём таблицы, если их ещё нет.
    """
    Base.metadata.create_all(bind=engine)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "users"}


# ---------- Эндпоинты для работы с пользователями ----------

@app.get("/users", response_model=List[User])
def list_users(db: Session = Depends(get_db)):
    """
    Вернуть список всех пользователей из БД.
    """
    users = db.query(UserORM).all()
    # преобразуем в Pydantic-модели
    return [
        User(id=user.id, username=user.username, email=user.email)
        for user in users
    ]


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Вернуть одного пользователя по id.
    Если пользователь не найден — 404.
    """
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return User(id=user.id, username=user.username, email=user.email)


@app.post("/users", response_model=User, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Создать нового пользователя.

    ID генерируется БД автоматически (AUTOINCREMENT).
    """
    # можно добавить простую проверку на уникальность username/email (опционально)
    existing = (
        db.query(UserORM)
        .filter(
            (UserORM.username == user_in.username)
            | (UserORM.email == user_in.email)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User with same username or email already exists",
        )

    user = UserORM(username=user_in.username, email=user_in.email)
    db.add(user)
    db.commit()
    db.refresh(user)

    return User(id=user.id, username=user.username, email=user.email)
