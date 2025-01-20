# Используем базовый образ с Python
FROM python:3.9-slim

# Указываем рабочую директорию
WORKDIR /app

# Устанавливаем системные библиотеки, включая необходимые для сборки C-расширений
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libpq-dev \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt /app/

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY . /app/

# Устанавливаем переменную окружения для Python
ENV PYTHONUNBUFFERED=1

# Команда для запуска приложения
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
