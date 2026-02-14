from nicegui import ui, app
import asyncio
import sys
import os
from dotenv import load_dotenv
import admin_page
from fastapi import Request # <--- НУЖНО ДЛЯ WEBHOOK

# Модули проекта
from frontend import init_ui 
from backend import background_task
from market_data import market_service_task 
from logger import log
from init_db import init_db_tables 
from payments import process_webhook # <--- ИМПОРТ ФУНКЦИИ ПЛАТЕЖЕЙ

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
app.on_startup(lambda: asyncio.create_task(market_service_task()))  # Рынок (CMC)

# === WEBHOOK ДЛЯ ОПЛАТЫ (ДОБАВЛЕНО) ===
@app.post("/api/payment/cryptocloud/webhook")
async def cryptocloud_webhook(request: Request):
    """
    Сюда CryptoCloud присылает уведомления об успешной оплате.
    """
    try:
        # Определяем тип контента (JSON или Form Data)
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            data = await request.json()
        else:
            form_data = await request.form()
            data = dict(form_data)

        log.info(f"💰 Webhook received: {data}")
        
        # Запускаем обработку (с проверкой через API)
        await process_webhook(data)
        
        return {"status": "ok"}
    except Exception as e:
        log.error(f"❌ Webhook Error: {e}")
        return {"status": "error"}

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