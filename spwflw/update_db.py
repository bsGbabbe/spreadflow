from db_session import engine
from models import Base
from sqlalchemy import text

def fix_database_schema():
    print("⚠️  НАЧИНАЕМ МИГРАЦИЮ ТАРИФОВ (СОХРАНЯЯ ЮЗЕРОВ) ...")
    
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        
        # 1. Сносим таблицы, которые вызывают конфликт (Тарифы, Подписки, Инвайты)
        # Мы обязаны это сделать, так как меняем тип Primary Key с UUID на String
        print("💥 Удаляем устаревшие таблицы (plans, subscriptions, invites)...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS plans CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS subscriptions CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS invites CASCADE;"))
            print("   -> Старые таблицы удалены.")
        except Exception as e:
            print(f"   -> Ошибка удаления (не критично): {e}")

    # 2. Создаем их заново по новым чертежам из models.py
    print("🏗️  Создаем таблицы заново с правильной структурой...")
    try:
        # SQLAlchemy сама увидит, что таблиц нет, и создаст их
        Base.metadata.create_all(bind=engine)
        print("✅  УСПЕШНО! Таблицы пересозданы.")
    except Exception as e:
        print(f"❌  ОШИБКА создания: {e}")

    print("\n🚀 Теперь перезапусти контейнер: docker-compose restart spreadflow_app")

if __name__ == "__main__":
    fix_database_schema()