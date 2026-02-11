# Используем легкий Python 3.10
FROM python:3.10-slim

# Рабочая папка внутри сервера
WORKDIR /app

# Копируем список библиотек и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь ваш код в сервер
COPY . .

# Открываем порт 8080
EXPOSE 8080

# Команда запуска
CMD ["python", "main.py"]