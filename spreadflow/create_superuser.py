import getpass
import bcrypt
from db_session import SessionLocal
from models import User, Subscription
from sqlalchemy.exc import IntegrityError

def create_superuser():
    print("--- СОЗДАНИЕ SUPERUSER (POSTGRESQL) ---")
    
    # 1. Сбор данных
    username = input("Введите логин (username): ").strip()
    email = input("Введите email: ").strip()
    password = getpass.getpass("Введите пароль (скрыт): ").strip()
    
    if not password:
        print("❌ Пароль не может быть пустым!")
        return

    # 2. Хеширование пароля (Bcrypt + Salt)
    # Это тот самый стандарт защиты, который мы обсуждали
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    # 3. Работа с базой данных
    db = SessionLocal()
    
    try:
        # Создаем пользователя
        new_admin = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            role='admin',        # Главная роль
            is_active=True,      # Доступ разрешен
            is_verified=True     # Почта подтверждена
        )
        db.add(new_admin)
        db.commit()            # Сохраняем, чтобы получить ID
        db.refresh(new_admin)  # Загружаем созданный ID

        # Создаем вечную подписку
        new_sub = Subscription(
            user_id=new_admin.id,
            plan_name='WHALE',   # Максимальный тариф
            is_active=True,
            end_date=None        # None означает "Навсегда"
        )
        db.add(new_sub)
        db.commit()
        
        print(f"\n✅ УСПЕХ! Администратор {username} создан.")
        print(f"🆔 ID: {new_admin.id}")
        print(f"💎 Тариф: WHALE (Lifetime)")
        
    except IntegrityError:
        db.rollback()
        print("\n❌ ОШИБКА: Такой пользователь или email уже существует.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_superuser()