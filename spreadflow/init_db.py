import time
import os
import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session
from db_session import engine, SessionLocal
from models import Base, User, Subscription, Plan # <--- Добавили Plan
from logger import log
from datetime import datetime

def init_db_tables():
    """
    1. Ждет базу данных.
    2. Создает таблицы.
    3. Создает тарифы (ЕСЛИ ИХ НЕТ).
    4. Создает первого админа (ЕСЛИ ЕГО НЕТ).
    """
    retries = 5
    while retries > 0:
        try:
            # Проверка соединения
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            log.info("--- DB: Connected to PostgreSQL. ---")
            
            # 1. Создаем таблицы
            Base.metadata.create_all(bind=engine)
            log.info("--- DB: Tables verified/created. ---")
            
            # 2. Создаем ТАРИФЫ (НОВОЕ)
            create_default_plans()
            
            # 3. Создаем Админа
            create_default_admin()
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
        
        # Список твоих тарифов
        plans_data = [
            {
                "name": "FREE", "price_str": "$0", "period_str": "/ forever", "css_color": "gray",
                "features": ["Только BTC/ETH", "Спреды до 1%", "Обновление 30 сек", "Без уведомлений"],
                "max_spread": 1, "refresh_rate": 30, "blur_hidden": True, "allow_click_links": False,
                "is_public": True
            },
            {
                "name": "START", "price_str": "$15", "period_str": "/ week", "css_color": "blue",
                "features": ["Топ-20 монет", "Спреды до 3%", "Обновление 15 сек", "Без уведомлений"],
                "max_spread": 3, "refresh_rate": 15, "blur_hidden": True, "allow_click_links": False,
                "is_public": True
            },
            {
                "name": "PRO", "price_str": "$40", "period_str": "/ week", "css_color": "green",
                "features": ["Все монеты (100+)", "Спреды до 10%", "Обновление 3 сек", "Telegram сигналы"],
                "max_spread": 10, "refresh_rate": 3, "blur_hidden": True, "allow_click_links": False,
                "is_public": True
            },
            {
                "name": "WHALE", "price_str": "$99", "period_str": "/ week", "css_color": "purple",
                "features": ["Полный доступ", "Безлимитные спреды", "Real-time (1 сек)", "Ссылки на биржи"],
                "max_spread": 9999, "refresh_rate": 1, "blur_hidden": False, "allow_click_links": True,
                "is_public": True
            }
        ]

        for p in plans_data:
            existing = db.query(Plan).get(p["name"])
            if not existing:
                new_plan = Plan(
                    name=p["name"], price_str=p["price_str"], period_str=p["period_str"],
                    css_color=p["css_color"], description_features=p["features"],
                    max_spread=p["max_spread"], refresh_rate=p["refresh_rate"],
                    blur_hidden=p["blur_hidden"], allow_click_links=p["allow_click_links"],
                    is_public=p["is_public"]
                )
                db.add(new_plan)
                log.info(f"--- INIT: Plan '{p['name']}' created. ---")
        
        db.commit()
        db.close()
    except Exception as e:
        log.error(f"--- INIT ERROR (Plans): {e} ---")

def create_default_admin():
    """Создает админа"""
    try:
        db = SessionLocal()
        admin_login = os.getenv("FIRST_ADMIN_LOGIN", "admin")
        admin_pass = os.getenv("FIRST_ADMIN_PASS", "admin123")
        
        existing_user = db.query(User).filter(User.username == admin_login).first()
        
        if not existing_user:
            log.info(f"--- INIT: Creating default admin '{admin_login}'... ---")
            pwd_bytes = admin_pass.encode('utf-8')
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
            
            new_admin = User(
                username=admin_login, email="admin@local.host", password_hash=hashed,
                role="admin", is_active=True, is_verified=True
            )
            db.add(new_admin)
            db.flush() 
            
            # Даем ему WHALE
            new_sub = Subscription(
                user_id=new_admin.id, plan_name="WHALE", is_active=True, start_date=datetime.utcnow()
            )
            db.add(new_sub)
            db.commit()
            log.info(f"--- INIT: Admin '{admin_login}' created! ---")
            
        db.close()
    except Exception as e:
        log.error(f"--- INIT ERROR (Admin): {e} ---")