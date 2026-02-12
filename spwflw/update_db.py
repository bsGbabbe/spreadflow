from database import engine
from sqlalchemy import text
from logger import log

def add_column_if_not_exists(table, column, col_type):
    try:
        with engine.connect() as conn:
            # Пытаемся выбрать колонку, если упадет - значит её нет
            conn.execute(text(f"SELECT {column} FROM {table} LIMIT 1"))
    except Exception:
        log.info(f"Adding column '{column}' to table '{table}'...")
        with engine.connect() as conn:
            # Для SQLite/Postgres синтаксис может чуть отличаться, но базовый ALTER TABLE работает везде
            # Если поле JSON/TEXT, дефолт нужен аккуратный
            default = "''" if "TEXT" in col_type or "VARCHAR" in col_type else "{}"
            if "FLOAT" in col_type or "INTEGER" in col_type:
                default = "0"
            
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"))
            conn.commit()
        log.info(f"Column '{column}' added successfully.")

def update_database_schema():
    log.info("Checking database schema updates...")
    
    # Добавляем новые поля в таблицу plans
    add_column_if_not_exists("plans", "description", "TEXT")
    add_column_if_not_exists("plans", "config", "JSON")
    add_column_if_not_exists("plans", "price", "FLOAT")
    add_column_if_not_exists("plans", "duration_days", "INTEGER")
    
    # Добавляем поле overrides в подписки
    add_column_if_not_exists("subscriptions", "custom_overrides", "JSON")
    
    log.info("Database schema is up to date.")

if __name__ == "__main__":
    update_database_schema()