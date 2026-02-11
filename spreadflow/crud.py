import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from models import Base, User, Subscription, ActivityLog, Invite, Plan, AdminNote
from db_session import SessionLocal

# --- СЕССИЯ ---
def get_db():
    """Создает сессию подключения к БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ПОЛЬЗОВАТЕЛИ (AUTH & READ) ---

def get_user_by_username(db: Session, username: str):
    """Находит пользователя по логину"""
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    """
    Проверяет логин и пароль.
    Возвращает объект User или None.
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    # Проверяем пароль через bcrypt
    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None

def get_all_users(db: Session):
    """Возвращает список всех пользователей (сначала новые)"""
    return db.query(User).order_by(User.created_at.desc()).all()

def search_users_db(db: Session, query_str: str):
    """
    Ищет пользователей по частичному совпадению
    в username, email или ID.
    """
    if not query_str:
        return get_all_users(db)
    
    search = f"%{query_str}%"
    
    return db.query(User).filter(
        or_(
            User.username.ilike(search),
            User.email.ilike(search),
            cast(User.id, String).ilike(search)
        )
    ).order_by(User.created_at.desc()).all()

# --- РЕГИСТРАЦИЯ И ИНВАЙТЫ ---

def check_invite(db: Session, code: str):
    """Проверяет, существует ли код и активен ли он"""
    invite = db.query(Invite).filter(Invite.code == code).first()
    if invite and invite.is_active and invite.used_count < invite.usage_limit:
        return invite
    return None

def get_all_invites(db: Session):
    """Список всех инвайтов"""
    return db.query(Invite).order_by(Invite.is_active.desc()).all()

def create_invite_db(db, code, plan_name, limit, days=0):
    """
    days: 0 или None = Вечная подписка
    days: > 0 = Подписка на N дней
    """
    # Если дней 0, записываем как None (вечно)
    duration = int(days) if days and int(days) > 0 else None
    
    new_invite = Invite(
        code=code, 
        plan_name=plan_name, 
        usage_limit=limit,
        duration_days=duration # Сохраняем длительность
    )
    db.add(new_invite)
    try:
        db.commit()
        return True, "Инвайт создан"
    except Exception as e:
        db.rollback()
        return False, str(e)

def register_user_with_invite(db, username, password, email, invite_code):
    # 1. Ищем инвайт
    invite = db.query(Invite).filter(Invite.code == invite_code).first()
    
    # Проверки инвайта
    if not invite:
        return False, "Неверный инвайт-код"
    if not invite.is_active:
        return False, "Инвайт отключен"
    if invite.used_count >= invite.usage_limit:
        return False, "Лимит использования инвайта исчерпан"

    # Проверка юзера
    if get_user_by_username(db, username):
        return False, "Пользователь с таким логином уже существует"

    try:
        # 2. Создаем юзера
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed,
            is_active=True,
            is_verified=True, # Сразу верифицируем, так как по инвайту
            role='user'
        )
        db.add(new_user)
        db.flush() # Получаем ID

        # 3. СЧИТАЕМ ДАТУ ОКОНЧАНИЯ ПОДПИСКИ
        start_date = datetime.utcnow()
        end_date = None # По умолчанию - вечно
        
        if invite.duration_days and invite.duration_days > 0:
            # Если в инвайте указаны дни, прибавляем их к текущей дате
            end_date = start_date + timedelta(days=invite.duration_days)

        # 4. Выдаем подписку
        new_sub = Subscription(
            user_id=new_user.id,
            plan_name=invite.plan_name,
            start_date=start_date,
            end_date=end_date, # <--- ТЕПЕРЬ ТУТ МОЖЕТ БЫТЬ ДАТА
            is_active=True
        )
        db.add(new_sub)

        # 5. Обновляем счетчик инвайта
        invite.used_count += 1
        
        create_activity_log(
            db, 
            user_id=new_user.id, 
            action="REGISTER", 
            details={"invite": invite_code} # Явно указываем details
        )
        
        db.commit()
        return True, "Регистрация успешна! Теперь войдите."
        
    except Exception as e:
        db.rollback()
        return False, f"Ошибка регистрации: {str(e)}"

# --- ПОДПИСКИ И ТАРИФЫ (USER SIDE) ---

def get_user_active_sub(db: Session, user_id):
    """Возвращает объект активной подписки (со всеми деталями)"""
    return db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).first()

def get_user_plan(db: Session, user_id):
    """Возвращает ТОЛЬКО название плана (строку)"""
    sub = get_user_active_sub(db, user_id)
    return sub.plan_name if sub else "FREE"

def upgrade_user_plan(db: Session, user_id: str, new_plan: str):
    """Смена тарифа (стандартная покупка)"""
    try:
        # Отключаем старую
        db.query(Subscription).filter(
            Subscription.user_id == user_id, 
            Subscription.is_active == True
        ).update({"is_active": False, "end_date": datetime.utcnow()})
        
        # Создаем новую
        new_sub = Subscription(
            user_id=user_id,
            plan_name=new_plan,
            is_active=True,
            start_date=datetime.utcnow()
        )
        db.add(new_sub)
        db.commit()
        return True, f"Тариф изменен на {new_plan}"
    except Exception as e:
        db.rollback()
        return False, str(e)

# --- УПРАВЛЕНИЕ ТАРИФАМИ (ADMIN SIDE) ---

def get_all_plans(db: Session):
    """Список всех доступных тарифов"""
    return db.query(Plan).all()

def get_plan_rules(db: Session, plan_name: str):
    """Получает настройки тарифа из БД"""
    plan = db.query(Plan).get(plan_name)
    if not plan:
        # Дефолтные настройки, если план не найден
        return {"max_spread": 1, "refresh_rate": 30, "blur_hidden": True, "allow_click_links": False}
    
    return {
        "max_spread": plan.max_spread,
        "refresh_rate": plan.refresh_rate,
        "blur_hidden": plan.blur_hidden,
        "allow_click_links": plan.allow_click_links
    }

def create_new_plan(db: Session, name: str, price: str, spread: int, speed: int, color: str):
    """Создать новый тариф"""
    try:
        new_plan = Plan(
            name=name.upper(),
            price_str=price,
            max_spread=spread,
            refresh_rate=speed,
            css_color=color,
            description_features=["Настраиваемый тариф"],
            is_public=True
        )
        db.add(new_plan)
        db.commit()
        return True, "Тариф создан"
    except Exception as e:
        db.rollback()
        return False, str(e)

def update_plan_details(db: Session, name: str, price: str, spread: int, speed: int, click: bool):
    """Обновить настройки существующего тарифа"""
    try:
        plan = db.query(Plan).get(name)
        if plan:
            plan.price_str = price
            plan.max_spread = spread
            plan.refresh_rate = speed
            plan.allow_click_links = click
            db.commit()
            return True
        return False
    except:
        db.rollback()
        return False

def delete_plan_db(db: Session, name: str):
    """Удалить тариф"""
    try:
        db.query(Plan).filter(Plan.name == name).delete()
        db.commit()
        return True
    except:
        db.rollback()
        return False

# --- ИНДИВИДУАЛЬНЫЕ НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ ---

def update_user_subscription_settings(db: Session, user_id: str, plan_name: str, overrides: dict = None):
    """
    Админ меняет тариф юзеру ИЛИ устанавливает персональные лимиты.
    """
    try:
        # 1. Закрываем старые
        db.query(Subscription).filter(
            Subscription.user_id == user_id, 
            Subscription.is_active == True
        ).update({"is_active": False, "end_date": datetime.utcnow()})
        
        # 2. Создаем новую с оверрайдами
        new_sub = Subscription(
            user_id=user_id,
            plan_name=plan_name,
            is_active=True,
            start_date=datetime.utcnow(),
            custom_overrides=overrides # JSON поле
        )
        db.add(new_sub)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error updating user sub: {e}")
        return False

# --- ЛОГИ И СТАТИСТИКА ---

def create_activity_log(db: Session, user_id, action, ip_address=None, details=None):
    """Запись действия в лог"""
    try:
        new_log = ActivityLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            details=details
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()  # Обязательно сбрасываем ошибочное состояние сессии
        print(f"Log Error: {e}") # Опционально для отладки

def get_recent_logs(db: Session, limit=50):
    """Получить последние логи с данными юзера"""
    return db.query(ActivityLog).join(User).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

def get_dashboard_stats(db: Session):
    """Статистика для админки"""
    total_users = db.query(User).count()
    active_invites = db.query(Invite).filter(Invite.is_active == True).count()
    whales = db.query(Subscription).filter(Subscription.plan_name == 'WHALE', Subscription.is_active == True).count()
    return total_users, active_invites, whales


def get_all_invites(db):
    """Получить список всех инвайтов (сначала новые)"""
    return db.query(Invite).order_by(Invite.id.desc()).all()

def delete_invite_db(db, invite_id):
    """Удалить инвайт по ID"""
    try:
        inv = db.query(Invite).filter(Invite.id == invite_id).first()
        if inv:
            db.delete(inv)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False


# ==========================================
#      УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (АДМИН)
# ==========================================

def get_user_active_sub(db, user_id):
    """Получает активную подписку конкретного пользователя"""
    return db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).first()

def update_user_subscription_settings(db, user_id, new_plan_name, overrides=None):
    """
    Меняет тариф юзера и его личные настройки (спред/скорость).
    overrides - это словарь типа {'max_spread': 50} или None (если сброс).
    """
    try:
        # 1. Ищем текущую подписку
        sub = get_user_active_sub(db, user_id)
        
        if sub:
            # Если есть - обновляем
            sub.plan_name = new_plan_name
            sub.custom_overrides = overrides # SQLAlchemy сам поймет, что JSON изменился
        else:
            # Если нет (вдруг удалилась) - создаем новую
            new_sub = Subscription(
                user_id=user_id,
                plan_name=new_plan_name,
                custom_overrides=overrides,
                is_active=True,
                start_date=datetime.utcnow()
            )
            db.add(new_sub)
            
        db.commit()
        return True, "Настройки пользователя обновлены"
    except Exception as e:
        db.rollback()
        return False, str(e)


# ==========================================
#        УПРАВЛЕНИЕ ТАРИФАМИ (МАГАЗИН)
# ==========================================

def get_all_plans(db):
    """Возвращает список всех тарифов"""
    return db.query(Plan).all()

def create_new_plan(db, name, price, spread, speed, color):
    """Создает новый тариф"""
    try:
        if db.query(Plan).get(name):
            return False, "Тариф с таким именем уже есть!"
            
        new_plan = Plan(
            name=name,
            price_str=price,
            max_spread=spread,
            refresh_rate=speed,
            css_color=color,
            is_public=True,
            description_features=["Autogenerated Plan"]
        )
        db.add(new_plan)
        db.commit()
        return True, "Тариф успешно создан"
    except Exception as e:
        db.rollback()
        return False, str(e)

def update_plan_details(db, name, price, spread, speed, smart_links):
    """Обновляет параметры существующего тарифа"""
    try:
        p = db.query(Plan).get(name)
        if p:
            p.price_str = price
            p.max_spread = spread
            p.refresh_rate = speed
            p.allow_click_links = smart_links
            db.commit()
            return True
        return False
    except:
        db.rollback()
        return False

def delete_plan_db(db, name):
    """Удаляет тариф"""
    try:
        p = db.query(Plan).get(name)
        if p:
            db.delete(p)
            db.commit()
            return True
        return False
    except:
        db.rollback()
        return False