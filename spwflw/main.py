from nicegui import ui, app
import asyncio
import sys
import os
from dotenv import load_dotenv
import admin_page


# Модули проекта
from frontend import init_ui 
from backend import background_task
from market_data import market_service_task # <--- ДОБАВЛЕНО
from logger import log
from init_db import init_db_tables 

# Роуты (не трогаем)
from user_profile import create_profile_route
from auth import create_auth_routes
from admin_page import create_admin_routes
from tariffs_page import create_tariffs_route

load_dotenv()

STORAGE_SECRET = os.getenv("STORAGE_SECRET")
if not STORAGE_SECRET:
    log.warning("⚠️ STORAGE_SECRET not found! Using default.")
    STORAGE_SECRET = "change_me_please_in_prod"

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Инициализация БД и UI
init_db_tables()
init_ui()

# Роуты
create_auth_routes()
create_profile_route()
create_tariffs_route()
create_admin_routes()

# Фоновые задачи
app.on_startup(lambda: asyncio.create_task(background_task()))      # Арбитраж
app.on_startup(lambda: asyncio.create_task(market_service_task()))  # Рынок (CMC) <--- ЗАПУСК

if __name__ in {"__main__", "__mp_main__"}:
    log.info("🚀 Starting SpreadFlow AI...")
    ui.run(
    title="SpreadFlow AI", 
    port=8080, 
    reload=False,
    show=False,
    storage_secret=STORAGE_SECRET, 
    favicon="🚀",
    reconnect_timeout=10.0  # <--- Увеличил таймаут, чтобы не рвало соединение при загрузке данных
)