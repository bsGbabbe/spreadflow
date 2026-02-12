import bcrypt
import smtplib
import random
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
# Импортируем обновленные модели
from models import Base, User, Subscription, ActivityLog, Invite, Plan, AdminNote
from db_session import SessionLocal
from config import SMTP_CONFIG
import uuid

# --- СЕССИЯ ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ОТПРАВКА ПОЧТЫ ---
def send_verification_email(to_email, code):
    if "your_email" in SMTP_CONFIG["user"]:
        print(f"\n[MOCK EMAIL] To: {to_email} | CODE: {code}\n")
        return True

    try:
        msg = MIMEText(f"Your verification code: {code}")
        msg['Subject'] = "SpreadFlow Verification"
        msg['From'] = SMTP_CONFIG['from_email']
        msg['To'] = to_email

        with smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.sendmail(SMTP_CONFIG['from_email'], [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

# --- ПОЛЬЗОВАТЕЛИ ---
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id):
    # Поддержка UUID
    return db.query(User).filter(User.id == user_id).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    # Если почта не подтверждена, не пускаем
    if not user.is_verified:
        return "unverified" 

    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None

def get_all_users(db: Session):
    return db.query(User).order_by(User.created_at.desc()).all()

def search_users_db(db: Session, query_str: str):
    if not query_str:
        return get_all_users(db)
    search = f"%{query_str}%"
    return db.query(User).filter(
        or_(User.username.ilike(search), User.email.ilike(search), cast(User.id, String).ilike(search))
    ).order_by(User.created_at.desc()).all()

# --- АДМИНСКОЕ УПРАВЛЕНИЕ ---
def get_user_active_sub(db: Session, user_id):
    return db.query(Subscription).filter(
        Subscription.user_id == user_id, 
        Subscription.is_active == True,
        Subscription.end_date > datetime.utcnow()
    ).first()

def update_user_admin_settings(db: Session, user_id, plan_name, role, is_verified, is_active, overrides=None):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = role
            user.is_verified = is_verified
            user.is_active = is_active
        
        sub = get_user_active_sub(db, user_id)
        if sub:
            sub.plan_name = plan_name
            sub.custom_overrides = overrides
        else:
            new_sub = Subscription(
                user_id=user_id, 
                plan_name=plan_name, 
                custom_overrides=overrides, 
                is_active=True, 
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30) # Default 30 days if new
            )
            db.add(new_sub)
            
        db.commit()
        return True, "Updated"
    except Exception as e:
        db.rollback()
        return False, str(e)

# --- ИНВАЙТЫ ---
def check_invite(db: Session, code: str):
    invite = db.query(Invite).filter(Invite.code == code).first()
    if invite and invite.is_active and invite.used_count < invite.usage_limit:
        return invite
    return None

def create_invite_db(db: Session, code, plan_name, limit, days=0):
    duration = int(days) if days and int(days) > 0 else None
    new_invite = Invite(code=code, plan_name=plan_name, usage_limit=limit, duration_days=duration)
    db.add(new_invite)
    try:
        db.commit()
        return True, "Created"
    except Exception as e:
        db.rollback()
        return False, str(e)

def get_all_invites(db: Session):
    return db.query(Invite).order_by(Invite.id.desc()).all()

def delete_invite_db(db: Session, invite_id):
    try:
        inv = db.query(Invite).filter(Invite.id == invite_id).first()
        if inv:
            db.delete(inv)
            db.commit()
            return True
        return False
    except:
        db.rollback()
        return False

# --- РЕГИСТРАЦИЯ (С КОДОМ) ---
def register_user_with_invite(db: Session, username, password, email, invite_code):
    invite = check_invite(db, invite_code)
    if not invite: return False, "Invalid or Expired Invite"
    
    # Проверка существующего пользователя
    existing_user = get_user_by_username(db, username)
    
    # Генерация хеша и кода
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    code = str(random.randint(100000, 999999))

    try:
        # Если юзер есть, но НЕ верифицирован -> обновляем данные и шлем код заново
        if existing_user and not existing_user.is_verified:
            existing_user.email = email
            existing_user.password_hash = hashed
            existing_user.verification_code = code
            db.commit()
            send_verification_email(email, code)
            return True, "Code resent to email"

        # Если юзер есть и верифицирован -> ошибка
        if existing_user:
            return False, "Username Taken"

        # Создаем нового
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed,
            is_active=True,
            is_verified=False, # Сначала false
            verification_code=code,
            role='user'
        )
        db.add(new_user)
        db.flush() # Получаем ID

        # Шлем письмо
        send_verification_email(email, code)

        # Создаем подписку
        start_date = datetime.utcnow()
        end_date = None
        
        # Берем длительность из инвайта или из плана
        days_to_add = 30 # Default
        if invite.duration_days and invite.duration_days > 0:
            days_to_add = invite.duration_days
        else:
            # Пытаемся взять из плана
            plan = db.query(Plan).filter(Plan.name == invite.plan_name).first()
            if plan and plan.duration_days:
                days_to_add = plan.duration_days
        
        end_date = start_date + timedelta(days=days_to_add)

        new_sub = Subscription(
            user_id=new_user.id,
            plan_name=invite.plan_name,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        db.add(new_sub)
        invite.used_count += 1
        
        create_activity_log(db, user_id=new_user.id, action="REGISTER_ATTEMPT", details={"invite": invite_code})
        db.commit()
        return True, "Code sent to email"
        
    except Exception as e:
        db.rollback()
        return False, f"Error: {str(e)}"

# --- ФИНАЛЬНАЯ ВЕРИФИКАЦИЯ ---
def verify_user_code(db: Session, username, code):
    user = get_user_by_username(db, username)
    if not user:
        return False, "User not found"
        
    if user.is_verified:
        return True, "Already verified"
        
    if user.verification_code == code:
        user.is_verified = True
        user.verification_code = None 
        db.commit()
        return True, "Success"
    else:
        return False, "Wrong code"

# --- ТАРИФЫ (PLANS) ---
def get_all_plans(db: Session): 
    return db.query(Plan).all()

def get_plan_by_name(db: Session, name: str):
    return db.query(Plan).filter(Plan.name == name).first()

def create_plan(db: Session, name, price, days, description="", config=None):
    if not config: config = {}
    
    # Legacy mapping
    price_str = f"${int(price)}"
    
    try:
        if get_plan_by_name(db, name): return False, "Exists"
        
        new_plan = Plan(
            name=name, 
            price=price,
            duration_days=days,
            description=description,
            config=config,
            # Legacy fields
            price_str=price_str,
            max_spread=config.get('max_spread', 1),
            refresh_rate=config.get('refresh_rate', 30),
            blur_hidden=config.get('blur_hidden', True),
            allow_click_links=config.get('allow_click_links', False),
            is_public=True
        )
        db.add(new_plan)
        db.commit()
        return True, "OK"
    except Exception as e:
        db.rollback()
        return False, str(e)

def update_plan(db: Session, plan_id, data: dict):
    # Пытаемся найти по ID (UUID) или по имени
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan and 'name' in data:
        plan = db.query(Plan).filter(Plan.name == data['name']).first()
            
    if plan:
        try:
            if 'name' in data: plan.name = data['name']
            if 'price' in data: 
                plan.price = data['price']
                plan.price_str = f"${int(data['price'])}" # Sync legacy
            if 'duration_days' in data: plan.duration_days = data['duration_days']
            if 'description' in data: plan.description = data['description']
            if 'config' in data: 
                plan.config = data['config']
                # Sync legacy fields from config
                cfg = data['config']
                if 'max_spread' in cfg: plan.max_spread = cfg['max_spread']
                if 'refresh_rate' in cfg: plan.refresh_rate = cfg['refresh_rate']
                if 'blur_hidden' in cfg: plan.blur_hidden = cfg['blur_hidden']
                if 'allow_click_links' in cfg: plan.allow_click_links = cfg['allow_click_links']
            
            if 'css_color' in data: plan.css_color = data['css_color']
            
            db.commit()
            db.refresh(plan)
            return True, "Updated"
        except Exception as e:
            db.rollback()
            return False, str(e)
    return False, "Not found"

def delete_plan_db(db: Session, name):
    try: 
        db.query(Plan).filter(Plan.name == name).delete() 
        db.commit()
        return True
    except: 
        db.rollback()
        return False

# --- ПОДПИСКИ ---
def get_user_plan(db, uid): 
    sub = get_user_active_sub(db, uid)
    return sub.plan_name if sub else "FREE"

def update_user_subscription_settings(db, uid, pname, ov=None):
    # Это wrapper для админской функции
    return update_user_admin_settings(db, uid, pname, 'user', True, True, ov)

def upgrade_user_plan(db: Session, user_id, new_plan_name: str, days: int = 30):
    try:
        plan = db.query(Plan).filter(Plan.name == new_plan_name).first()
        if not plan: return False, "Plan not found"
        
        # Deactivate old
        db.query(Subscription).filter(Subscription.user_id == user_id, Subscription.is_active == True).update({"is_active": False})
        
        # Create new
        actual_days = plan.duration_days if plan.duration_days else days
        
        new_sub = Subscription(
            user_id=user_id, plan_name=new_plan_name,
            start_date=datetime.utcnow(), 
            end_date=datetime.utcnow() + timedelta(days=actual_days),
            is_active=True
        )
        db.add(new_sub)
        db.commit()
        return True, f"Upgraded to {new_plan_name}"
    except Exception as e:
        db.rollback()
        return False, str(e)

# --- ЛОГИ ---
def create_activity_log(db: Session, user_id, action, ip_address=None, details=None):
    try: 
        db.add(ActivityLog(user_id=user_id, action=action, ip_address=ip_address, details=details))
        db.commit()
    except: 
        db.rollback()

def get_recent_logs(db: Session, limit=50): 
    return db.query(ActivityLog).join(User).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

def get_dashboard_stats(db):
    return (
        db.query(User).count(), 
        db.query(Invite).filter(Invite.is_active==True).count(), 
        db.query(Subscription).filter(Subscription.plan_name=='WHALE', Subscription.is_active==True).count()
    )