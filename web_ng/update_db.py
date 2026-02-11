from db_session import SessionLocal
from sqlalchemy import text

def fix_database():
    print("--- ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ ---")
    db = SessionLocal()
    
    # 1. Добавляем custom_overrides в subscriptions
    try:
        print("1. Добавляем custom_overrides в subscriptions...")
        db.execute(text("ALTER TABLE subscriptions ADD COLUMN custom_overrides JSON;"))
        db.commit()
        print("✅ Успешно!")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Пропущено (возможно, уже есть): {e}")

    # 2. Добавляем is_public в plans (мы это тоже добавляли в models.py)
    try:
        print("2. Добавляем is_public в plans...")
        db.execute(text("ALTER TABLE plans ADD COLUMN is_public BOOLEAN DEFAULT TRUE;"))
        db.commit()
        print("✅ Успешно!")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Пропущено (возможно, уже есть): {e}")
        
    db.close()
    print("--- ГОТОВО ---")

if __name__ == "__main__":
    fix_database()