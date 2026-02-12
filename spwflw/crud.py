import bcrypt
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from models import User, Subscription, ActivityLog, Invite, Plan
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

def verify_user_code(db: Session, code: str):
    """
    FIX: Алиас для совместимости со старым auth.py.
    Делает то же самое, что и check_invite.
    """
    return check_invite(db, code)

def get_all_invites(db: Session):
    """Список всех инвайтов"""
    return db.query(Invite).order_by(Invite.is_active.desc()).all()

def create_invite_db(db: Session, code: str, plan: str, limit: int):
    """Создание инвайта администратором"""
    try:
        new_invite = Invite(code=code, plan_name=plan, usage_limit=limit)
        db.add(new_invite)
        db.commit()
        return True, "Инвайт создан"
    except Exception as e:
        db.rollback()
        return False, str(e)

def register_user_with_invite(db: Session, username, password, email, invite_code):
    """Регистрация: Создаем Юзера + Подписку по коду инвайта"""
    
    # 1. Проверяем инвайт
    invite = check_invite(db, invite_code)
    if not invite:
        return False, "Неверный или неактивный инвайт-код"

    # 2. Хешируем пароль
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    try:
        # 3. Создаем пользователя
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            role='user',
            is_active=True
        )
        db.add(new_user)
        db.flush() # Получаем ID до коммита

        # 4. Выдаем подписку согласно инвайту
        new_sub = Subscription(
            user_id=new_user.id,
            plan_name=invite.plan_name,
            is_active=True,
            start_date=datetime.utcnow()
        )
        db.add(new_sub)

        # 5. Обновляем счетчик инвайта
        invite.used_count += 1
        
        db.commit()
        return True, "Аккаунт успешно создан!"
        
    except Exception as e:
        db.rollback()
        return False, f"Ошибка базы данных (возможно логин занят): {e}"

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

# --- УПРАВЛЕНИЕ ТАРИФАМИ (ADMIN SIDE - GOD MODE) ---

def get_all_plans(db: Session):
    """Список всех доступных тарифов"""
    return db.query(Plan).all()

def get_plan_by_name(db: Session, name: str):
    """Получить объект тарифа (FIX: добавлен для совместимости)"""
    return db.query(Plan).get(name)

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
        "allow_click_links": plan.allow_click_links,
        # FIX: Учитываем поле allow_telegram, если оно есть в модели (безопасное чтение)
        "allow_telegram": getattr(plan, 'allow_telegram', False) 
    }

def create_new_plan(db: Session, name: str, price: str, spread: int, speed: int, color: str):
    """Создать новый базовый тариф"""
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

def update_plan_details(db: Session, name: str, 
                        price: str, period: str, color: str, is_public: bool,
                        spread: int, speed: int, 
                        blur: bool, telegram: bool, click: bool,
                        features: list):
    """
    GOD MODE: Обновление АБСОЛЮТНО ВСЕХ параметров тарифа.
    """
    try:
        plan = db.query(Plan).get(name)
        if plan:
            # 1. Визуальная часть
            plan.price_str = price
            plan.period_str = period
            plan.css_color = color
            plan.is_public = is_public
            
            # 2. Лимиты
            plan.max_spread = spread
            plan.refresh_rate = speed
            
            # 3. Доступы
            plan.blur_hidden = blur
            plan.allow_telegram = telegram
            plan.allow_click_links = click
            
            # 4. Фичи (список)
            plan.description_features = features
            
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating plan: {e}")
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
    Админ меняет тариф юзеру ИЛИ устанавливает персональные лимиты (overrides).
    Если тариф остается тем же, мы просто обновляем JSON overrides,
    не сбрасывая дату начала подписки.
    """
    try:
        current_sub = get_user_active_sub(db, user_id)
        
        # Сценарий 1: Тариф тот же, меняем только настройки
        if current_sub and current_sub.plan_name == plan_name:
            current_sub.custom_overrides = overrides
            db.commit()
            return True

        # Сценарий 2: Смена тарифа (или создание новой подписки)
        if current_sub:
            current_sub.is_active = False
            current_sub.end_date = datetime.utcnow()
        
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
    except:
        pass # Логи не должны ломать основную работу

def get_recent_logs(db: Session, limit=50):
    """Получить последние логи с данными юзера"""
    return db.query(ActivityLog).join(User).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

def get_dashboard_stats(db: Session):
    """Статистика для админки"""
    total_users = db.query(User).count()
    active_invites = db.query(Invite).filter(Invite.is_active == True).count()
    whales = db.query(Subscription).filter(Subscription.plan_name == 'WHALE', Subscription.is_active == True).count()
    return total_users, active_invites, whales