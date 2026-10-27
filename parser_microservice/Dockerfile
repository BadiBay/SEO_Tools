# Используем официальный образ Python
FROM python:3.11-slim

# Настройка переменных окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Обновляем систему и ставим базовые утилиты
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузеры для Playwright и их системные зависимости
RUN playwright install chromium --with-deps

# Копируем весь исходный код проекта
COPY . .

# Открываем порт для FastAPI
EXPOSE 8000

# Команда для запуска приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
