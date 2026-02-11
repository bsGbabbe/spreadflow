from nicegui import ui, app
import asyncio
import sys
import os


# Импорты
from frontend import create_ui
from backend import background_task
from logger import log
from user_profile import create_profile_route
from auth import create_auth_routes
from admin_page import create_admin_routes # <--- НОВОЕ
from database import init_db # Это старое, можно убрать если используем init_db.py отдельно, но не мешает
from tariffs_page import create_tariffs_route
from dotenv import load_dotenv
from tariffs_page import create_tariffs_route


load_dotenv() # Загружаем .env
SECRET = os.getenv("STORAGE_SECRET")

# Исправление для Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Фоновая задача
app.on_startup(lambda: asyncio.create_task(background_task()))

# РЕГИСТРАЦИЯ МАРШРУТОВ
create_auth_routes()    # /login, /register

create_profile_route()  # /profile
create_tariffs_route()
create_admin_routes()   # /admin <-- ДОБАВЛЕНО

# Главная страница
@ui.page('/')
def main_page():
    create_ui()

if __name__ in {"__main__", "__mp_main__"}:
    log.info("Starting SpreadFlow AI...")
    ui.run(title="SpreadFlow AI", port=8080, reload=False, show=True, storage_secret='7f8s9d0f7s89d7f0s8d7f0s8d7f0s8d7f0s8d7f')