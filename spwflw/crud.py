import bcrypt
import smtplib
import random
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from models import User, Subscription, ActivityLog, Invite, Plan
from db_session import SessionLocal
from config import SMTP_CONFIG
from logger import log

# --- СЕССИЯ ---
def get_db():
    """Создает сессию подключения к БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ОТПРАВКА ПОЧТЫ (ВОССТАНОВЛЕНО) ---
def send_verification_email(to_email, code):
    """
    Отправляет код верификации через SMTP.
    Использует системное логирование для отладки.
    """
    try:
        msg = MIMEText(f"Ваш код верификации для SpreadFlow AI: {code}")
        msg['Subject'] = "SpreadFlow Verification Code"
        msg['From'] = SMTP_CONFIG['from_email']
        msg['To'] = to_email

        log.info(f"Попытка отправки письма на {to_email}...")

        # Таймаут 10 сек, чтобы интерфейс не зависал
        with smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'], timeout=10) as server:
            server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.sendmail(SMTP_CONFIG['from_email'], [to_email], msg.as_string())
        
        log.info(f"✅ Письмо успешно отправлено на {to_email}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка SMTP: {str(e)}")
        return False

# --- ПОЛЬЗОВАТЕЛИ (AUTH & READ) ---

def get_user_by_username(db: Session, username: str):
    """Находит пользователя по логину"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """Находит пользователя по почте"""
    return db.query(User).filter(User.email == email).first()

def get_user_email(db: Session, username: str):
    """Возвращает скрытый email пользователя для отображения в UI"""
    user = get_user_by_username(db, username)
    if user:
        return user.email
    return None

def authenticate_user(db: Session, username: str, password: str):
    """
    Проверяет логин, пароль и статус верификации.
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        # Проверка верификации
        if hasattr(user, 'is_verified') and not user.is_verified:
            return "unverified"
        return user
    return None

def update_user_password(db: Session, username: str, new_password: str):
    """
    Обновляет пароль пользователя (хеширует и сохраняет).
    """
    user = get_user_by_username(db, username)
    if not user:
        return False, "Пользователь не найден"
    
    try:
        salt = bcrypt.gensalt()
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
        user.password_hash = hashed_pw
        db.commit()
        return True, "Пароль успешно изменен"
    except Exception as e:
        db.rollback()
        log.error(f"Error updating password: {e}")
        return False, f"Ошибка при смене пароля: {str(e)}"

def get_all_users(db: Session):
    """Возвращает список всех пользователей (сначала новые)"""
    return db.query(User).order_by(User.created_at.desc()).all()

def search_users_db(db: Session, query_str: str):
    """Поиск пользователей по базе"""
    if not query_str:
        return get_all_users(db)
    search = f"%{query_str}%"
    return db.query(User).filter(
        or_(User.username.ilike(search), User.email.ilike(search), cast(User.id, String).ilike(search))
    ).order_by(User.created_at.desc()).all()

# --- РЕГИСТРАЦИЯ И ИНВАЙТЫ ---

def delete_invite_db(db: Session, invite_id: str):
    """Удаление инвайта по ID"""
    try:
        # Ищем по ID (так надежнее чем по коду)
        db.query(Invite).filter(Invite.id == invite_id).delete()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False

def check_invite(db: Session, code: str):
    """Проверяет инвайт на существование и лимиты"""
    invite = db.query(Invite).filter(Invite.code == code).first()
    if invite and invite.is_active and invite.used_count < invite.usage_limit:
        return invite
    return None

def verify_user_code(db: Session, username: str, code: str):
    """
    Проверяет код из письма и активирует аккаунт.
    """
    user = get_user_by_username(db, username)
    if user and user.verification_code == code:
        user.is_verified = True
        user.verification_code = None
        db.commit()
        return True, "Успешно"
    return False, "Неверный код"

def resend_verification_code(db: Session, username: str, new_email: str = None):
    """
    Генерирует новый код и отправляет его.
    Позволяет сменить email, если пользователь ошибся при регистрации.
    """
    user = get_user_by_username(db, username)
    if not user:
        return False, "Пользователь не найден"
    
    if user.is_verified:
        return False, "Аккаунт уже подтвержден"
    
    # Если передан новый email - обновляем его
    if new_email and new_email != user.email:
        # Проверяем, не занят ли он
        if get_user_by_email(db, new_email):
            return False, "Этот email уже занят другим пользователем"
        user.email = new_email
    
    # Генерация нового кода
    new_code = str(random.randint(100000, 999999))
    user.verification_code = new_code
    db.commit()
    
    # Отправка
    if send_verification_email(user.email, new_code):
        return True, f"Код отправлен на {user.email}"
    else:
        return False, "Ошибка отправки письма (проверьте логи)"

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
    """
    Регистрация: Проверка -> Создание (is_verified=False) -> Отправка Email.
    """
    # 1. Проверки
    invite = check_invite(db, invite_code)
    if not invite: 
        return False, "Неверный или неактивный инвайт-код"
    
    if get_user_by_username(db, username): 
        return False, "Этот логин уже занят"
    
    if get_user_by_email(db, email): 
        return False, "Эта почта уже зарегистрирована"

    # 2. Подготовка
    salt = bcrypt.gensalt()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    v_code = str(random.randint(100000, 999999))

    try:
        # 3. Создаем пользователя
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            role='user',
            is_active=True,
            is_verified=False,
            verification_code=v_code
        )
        db.add(new_user)
        db.flush()

        # 4. Отправка письма
        if not send_verification_email(email, v_code):
            db.rollback()
            return False, "Ошибка отправки письма. Проверьте настройки SMTP."

        # 5. Выдача подписки
        new_sub = Subscription(
            user_id=new_user.id,
            plan_name=invite.plan_name,
            is_active=True,
            start_date=datetime.utcnow()
        )
        db.add(new_sub)

        invite.used_count += 1
        db.commit()
        log.info(f"Пользователь {username} зарегистрирован, код отправлен.")
        return True, "Код отправлен на почту!"
        
    except Exception as e:
        db.rollback()
        log.error(f"Ошибка регистрации: {e}")
        return False, f"Ошибка базы данных: {e}"

# --- ПОДПИСКИ И ТАРИФЫ (USER SIDE) ---

def get_user_active_sub(db: Session, user_id):
    """Возвращает активную подписку"""
    return db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).first()

def get_user_plan(db: Session, user_id):
    """Возвращает название плана"""
    sub = get_user_active_sub(db, user_id)
    return sub.plan_name if sub else "FREE"

def upgrade_user_plan(db: Session, user_id: str, new_plan: str):
    """Смена тарифа"""
    try:
        db.query(Subscription).filter(
            Subscription.user_id == user_id, 
            Subscription.is_active == True
        ).update({"is_active": False, "end_date": datetime.utcnow()})
        
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
    """Получить объект тарифа по имени"""
    return db.query(Plan).get(name)

def get_plan_rules(db: Session, plan_name: str):
    """Получает настройки тарифа из БД"""
    plan = db.query(Plan).get(plan_name)
    if not plan:
        return {"max_spread": 1, "refresh_rate": 30, "blur_hidden": True, "allow_click_links": False}
    
    return {
        "max_spread": plan.max_spread,
        "refresh_rate": plan.refresh_rate,
        "blur_hidden": plan.blur_hidden,
        "allow_click_links": plan.allow_click_links,
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
    """GOD MODE: Обновление всех параметров тарифа"""
    try:
        plan = db.query(Plan).get(name)
        if plan:
            plan.price_str = price
            plan.period_str = period
            plan.css_color = color
            plan.is_public = is_public
            plan.max_spread = spread
            plan.refresh_rate = speed
            plan.blur_hidden = blur
            plan.allow_telegram = telegram
            plan.allow_click_links = click
            plan.description_features = features
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        log.error(f"Error updating plan: {e}")
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
    """Обновление подписки и персональных лимитов"""
    try:
        current_sub = get_user_active_sub(db, user_id)
        
        if current_sub and current_sub.plan_name == plan_name:
            current_sub.custom_overrides = overrides
            db.commit()
            return True

        if current_sub:
            current_sub.is_active = False
            current_sub.end_date = datetime.utcnow()
        
        new_sub = Subscription(
            user_id=user_id,
            plan_name=plan_name,
            is_active=True,
            start_date=datetime.utcnow(),
            custom_overrides=overrides 
        )
        db.add(new_sub)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        log.error(f"Error updating user sub: {e}")
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
        db.rollback()

def get_recent_logs(db: Session, limit=50):
    """Последние логи с данными юзера"""
    return db.query(ActivityLog).join(User).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

def get_dashboard_stats(db: Session):
    """Статистика для админки"""
    total_users = db.query(User).count()
    active_invites = db.query(Invite).filter(Invite.is_active == True).count()
    whales = db.query(Subscription).filter(Subscription.plan_name == 'WHALE', Subscription.is_active == True).count()
    return total_users, active_invites, whales