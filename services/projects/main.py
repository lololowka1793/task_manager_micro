from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ---------- Pydantic-модели ----------

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: int  # id пользователя-владельца (пока просто число)


class Project(ProjectBase):
    id: int


class ProjectCreate(ProjectBase):
    """Модель для создания проекта (без id)."""
    pass


# ---------- "База данных" в памяти ----------

PROJECTS_DB: List[Project] = [
    Project(
        id=1,
        name="Demo Project",
        description="Первый демо-проект",
        owner_id=1,
    ),
    Project(
        id=2,
        name="Учебный проект по PAD",
        description="Проект для лабораторной по микросервисам",
        owner_id=2,
    ),
]


# ---------- Приложение FastAPI ----------

app = FastAPI(title="Projects Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "projects"}


# ---------- Эндпоинты для работы с проектами ----------

@app.get("/projects", response_model=List[Project])
async def list_projects():
    """
    Вернуть список всех проектов.
    """
    return PROJECTS_DB


@app.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: int):
    """
    Вернуть один проект по id.
    Если проект не найден — 404.
    """
    for project in PROJECTS_DB:
        if project.id == project_id:
            return project
    raise HTTPException(status_code=404, detail="Project not found")


@app.post("/projects", response_model=Project, status_code=201)
async def create_project(project_in: ProjectCreate):
    """
    Создать новый проект.

    ID генерируется как max_id + 1.
    """
    if PROJECTS_DB:
        max_id = max(project.id for project in PROJECTS_DB)
    else:
        max_id = 0

    new_project = Project(
        id=max_id + 1,
        name=project_in.name,
        description=project_in.description,
        owner_id=project_in.owner_id,
    )
    PROJECTS_DB.append(new_project)
    return new_project


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: int):
    """
    Удалить проект по id.

    Если проект не найден — 404.
    """
    for index, project in enumerate(PROJECTS_DB):
        if project.id == project_id:
            PROJECTS_DB.pop(index)
            return

    raise HTTPException(status_code=404, detail="Project not found")
