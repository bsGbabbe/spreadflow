import time
import os
import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session
# Импортируем engine и фабрику сессий
from db_session import engine, SessionLocal
# Импортируем ВСЕ модели, чтобы SQLAlchemy знала, какие таблицы создавать
from models import Base, User, Subscription, Plan, Invite, ActivityLog, AdminNote
from logger import log
from datetime import datetime

def init_db_tables():
    """
    1. Ждет базу данных (Postgres).
    2. Создает таблицы, если их нет.
    3. Создает тарифы (если таблица пустая или тариф отсутствует).
    4. Создает первого админа (если его нет).
    """
    retries = 25
    while retries > 0:
        try:
            # Проверка соединения
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            log.info("--- DB: Connected to PostgreSQL. ---")
            
            # 1. Создаем ВСЕ таблицы (User, Plan, Subscription, Invite и др.)
            Base.metadata.create_all(bind=engine)
            log.info("--- DB: Tables verified/created. ---")
            
            # 2. Создаем/Проверяем тарифы
            create_default_plans()
            
            # 3. Создаем Админа
            create_default_admin()
            
            log.info("--- DB: Initialization complete. ---")
            return
            
        except Exception as e:
            log.warning(f"--- DB Not ready: {e}. Retrying in 2s... ---")
            time.sleep(2)
            retries -= 1
            
    log.error("--- DB: Could not connect after retries ---")

def create_default_plans():
    """Наполняет базу стандартными тарифами"""
    try:
        db = SessionLocal()
        
        # Настройки тарифов (как в твоем ТЗ)
        plans_data = [
            {
                "name": "FREE", 
                "price_str": "$0", 
                "period_str": "/ forever", 
                "css_color": "gray",
                "features": ["Только BTC/ETH", "Спреды до 1%", "Обновление 30 сек", "Без уведомлений"],
                "max_spread": 1, 
                "refresh_rate": 30, 
                "blur_hidden": True, 
                "allow_click_links": False,
                "is_public": True
            },
            {
                "name": "START", 
                "price_str": "$15", 
                "period_str": "/ week", 
                "css_color": "blue",
                "features": ["Топ-20 монет", "Спреды до 3%", "Обновление 15 сек", "Без уведомлений"],
                "max_spread": 3, 
                "refresh_rate": 15, 
                "blur_hidden": True, 
                "allow_click_links": False,
                "is_public": True
            },
            {
                "name": "PRO", 
                "price_str": "$40", 
                "period_str": "/ week", 
                "css_color": "green",
                "features": ["Все монеты (100+)", "Спреды до 10%", "Обновление 3 сек", "Telegram сигналы"],
                "max_spread": 10, 
                "refresh_rate": 3, 
                "blur_hidden": True, 
                "allow_click_links": False,
                "is_public": True
            },
            {
                "name": "WHALE", 
                "price_str": "$99", 
                "period_str": "/ week", 
                "css_color": "purple",
                "features": ["Полный доступ", "Безлимитные спреды", "Real-time (1 сек)", "Ссылки на биржи"],
                "max_spread": 9999, 
                "refresh_rate": 1, 
                "blur_hidden": False, 
                "allow_click_links": True,
                "is_public": True
            }
        ]

        for p in plans_data:
            # Проверяем, есть ли такой тариф
            existing = db.query(Plan).get(p["name"])
            if not existing:
                new_plan = Plan(
                    name=p["name"], 
                    price_str=p["price_str"], 
                    period_str=p["period_str"],
                    css_color=p["css_color"], 
                    description_features=p["features"],
                    max_spread=p["max_spread"], 
                    refresh_rate=p["refresh_rate"],
                    blur_hidden=p["blur_hidden"], 
                    allow_click_links=p["allow_click_links"],
                    is_public=p["is_public"]
                )
                db.add(new_plan)
                log.info(f"--- INIT: Plan '{p['name']}' created. ---")
            else:
                # Опционально: можно обновлять поля, если они изменились, но пока оставим как есть
                pass
        
        db.commit()
        db.close()
    except Exception as e:
        log.error(f"--- INIT ERROR (Plans): {e} ---")

def create_default_admin():
    """Создает супер-админа, если его нет"""
    try:
        db = SessionLocal()
        # Берем логин/пароль из переменных окружения или дефолтные
        admin_login = os.getenv("FIRST_ADMIN_LOGIN", "admin")
        admin_pass = os.getenv("FIRST_ADMIN_PASS", "admin123")
        
        # Ищем пользователя с таким именем
        existing_user = db.query(User).filter(User.username == admin_login).first()
        
        if not existing_user:
            log.info(f"--- INIT: Creating default admin '{admin_login}'... ---")
            
            # Хешируем пароль (bcrypt требует bytes)
            pwd_bytes = admin_pass.encode('utf-8')
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
            
            # Создаем пользователя
            new_admin = User(
                username=admin_login,
                email="admin@spreadflow.ai", # Можно поменять на свой
                password_hash=hashed,
                role="admin",
                is_active=True,
                is_verified=True, # Админ сразу верифицирован
                verification_code=None
            )
            db.add(new_admin)
            db.flush() # Чтобы получить ID нового юзера до коммита
            
            # Даем ему подписку WHALE навсегда (или на 100 лет)
            new_sub = Subscription(
                user_id=new_admin.id,
                plan_name="WHALE",
                is_active=True,
                start_date=datetime.utcnow(),
                end_date=None # None = навсегда
            )
            db.add(new_sub)
            
            db.commit()
            log.info(f"--- INIT: Admin '{admin_login}' created successfully! ---")
        else:
            log.info(f"--- INIT: Admin '{admin_login}' already exists. ---")
            
        db.close()
    except Exception as e:
        log.error(f"--- INIT ERROR (Admin): {e} ---")

# === ГЛАВНАЯ ТОЧКА ВХОДА ===
if __name__ == "__main__":
    print("🚀 Starting manual DB initialization...")
    init_db_tables()
    print("✅ Initialization script finished.")