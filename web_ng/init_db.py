from db_session import engine
from models import Base

# Импортируем модели, чтобы SQLAlchemy знала, что создавать
# (даже если они не используются в этом файле напрямую)
from models import User, ActivityLog, AdminNote, Subscription

def init_db():
    print("--- НАЧАЛО СОЗДАНИЯ ТАБЛИЦ (POSTGRESQL) ---")
    try:
        # Эта команда берет все классы, унаследованные от Base,
        # и создает соответствующие таблицы в базе данных
        Base.metadata.create_all(bind=engine)
        print("✅ УСПЕХ: Таблицы созданы!")
        print("   - users")
        print("   - subscriptions")
        print("   - activity_logs")
        print("   - admin_notes")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        print("Проверьте, запущен ли PostgreSQL и правильный ли пароль в .env")

if __name__ == "__main__":
    init_db()