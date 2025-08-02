FROM python:3.11

# Установка зависимостей
WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y gcc libpq-dev && apt-get clean

# Копирование файлов
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
