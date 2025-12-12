FROM python:3.12-slim

WORKDIR /app

# Скопировать зависимости из корня проекта
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код конкретного сервиса
COPY services/users /app

# Для users-сервиса: порт 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
