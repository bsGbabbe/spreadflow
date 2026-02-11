from nicegui import ui, app
import asyncio
import sys
import os
from dotenv import load_dotenv

# --- ИМПОРТЫ МОДУЛЕЙ ПРОЕКТА ---
from frontend import create_ui
from backend import background_task
from logger import log
from user_profile import create_profile_route
from auth import create_auth_routes
from admin_page import create_admin_routes
from tariffs_page import create_tariffs_route

# --- НОВАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ (PostgreSQL) ---
# Мы используем новый init_db.py вместо старого database.py
from init_db import init_db_tables 

# 1. Загружаем переменные окружения (.env)
load_dotenv()

# Проверяем наличие ключа шифрования сессий
STORAGE_SECRET = os.getenv("STORAGE_SECRET")
if not STORAGE_SECRET:
    log.warning("⚠️ STORAGE_SECRET not found in .env! Using insecure default for dev.")
    STORAGE_SECRET = "change_me_please_in_prod"

# Исправление ошибки EventLoop для Windows (если запускаешь локально)
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 2. Инициализируем таблицы БД (синхронно, до запуска сервера)
# Это создаст таблицы в Postgres, если их еще нет
init_db_tables()

# 3. Регистрируем фоновую задачу (сканер рынков)
# Она запустится сразу после старта сервера
app.on_startup(lambda: asyncio.create_task(background_task()))

# --- РЕГИСТРАЦИЯ МАРШРУТОВ (ROUTES) ---
create_auth_routes()     # /login, /register
create_profile_route()   # /profile
create_tariffs_route()   # /tariffs
create_admin_routes()    # /admin

# --- ГЛАВНАЯ СТРАНИЦА ---
@ui.page('/')
def main_page():
    # Проверка авторизации внутри create_ui или здесь, если нужно
    create_ui()

# --- ЗАПУСК ПРИЛОЖЕНИЯ ---
if __name__ in {"__main__", "__mp_main__"}:
    log.info("🚀 Starting SpreadFlow AI...")
    
    ui.run(
        title="SpreadFlow AI", 
        port=8080, 
        reload=False,         # На проде reload лучше выключать
        show=False,           # На сервере браузер не открываем
        storage_secret=STORAGE_SECRET, # Секрет из .env
        favicon="🚀"
    )