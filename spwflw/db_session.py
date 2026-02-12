import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# 1. Загружаем секреты из файла .env
load_dotenv()

# Получаем данные
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 2. Формируем строку подключения
# Вид: postgresql://user:password@localhost:5432/dbname
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

if not DB_PASS:
    print("❌ ОШИБКА: Не найден пароль в файле .env!")
    exit(1)

# 3. Создаем "Движок" (Engine)
# pool_pre_ping=True помогает не терять связь при долгом простое
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# 4. Создаем фабрику сессий
# scoped_session гарантирует, что в разных потоках будут разные сессии (потокобезопасность)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    """
    Функция для получения сессии базы данных.
    Используйте её в коде так:
    with get_db() as db:
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()