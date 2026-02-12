import bcrypt
import smtplib
import random
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from models import User, Subscription, ActivityLog, Invite, Plan, AdminNote
from db_session import SessionLocal
from config import SMTP_CONFIG

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

# --- ПОЛЬЗОВАТЕЛИ (БАЗОВЫЕ) ---
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()

def get_all_users(db: Session):
    return db.query(User).order_by(User.created_at.desc()).all()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user: return None
    if not user.is_verified: return "unverified" 
    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None

# --- УПРАВЛЕНИЕ ПОДПИСКАМИ И ЛИМИТАМИ (ДЛЯ АДМИНКИ И ПРОФИЛЯ) ---
def get_user_active_sub(db: Session, user_id):
    return db.query(Subscription).filter(Subscription.user_id == user_id, Subscription.is_active == True).first()

def get_user_plan(db: Session, user_id):
    """Возвращает название плана пользователя (нужно для user_profile.py)"""
    sub = get_user_active_sub(db, user_id)
    return sub.plan_name if sub else "FREE"

def update_user_admin_settings(db: Session, user_id, plan_name, role, is_verified, is_active, overrides=None):
    """Главная функция админки для управления юзером и его личными лимитами (overrides)"""
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
                start_date=datetime.utcnow()
            )
            db.add(new_sub)
        db.commit()
        return True, "Updated"
    except Exception as e:
        db.rollback()
        return False, str(e)

# --- ТАРИФЫ (УПРАВЛЕНИЕ КОНСТРУКТОРОМ) ---
def get_all_plans(db: Session):
    return db.query(Plan).all()

def get_plan_by_name(db: Session, name: str):
    return db.query(Plan).filter(Plan.name == name).first()

def get_plan_rules(db: Session, plan_name: str):
    """Получает лимиты тарифа (нужно для tariffs.py)"""
    plan = get_plan_by_name(db, plan_name)
    if not plan:
        return {"max_spread": 1, "refresh_rate": 30, "blur_hidden": True, "allow_click_links": False}
    return {
        "max_spread": plan.max_spread,
        "refresh_rate": plan.refresh_rate,
        "blur_hidden": plan.blur_hidden,
        "allow_click_links": plan.allow_click_links
    }

def create_new_plan(db: Session, name, price, spread, speed, color):
    try:
        if get_plan_by_name(db, name): return False, "Exists"
        new_plan = Plan(name=name, price_str=price, max_spread=spread, refresh_rate=speed, css_color=color, is_public=True)
        db.add(new_plan)
        db.commit()
        return True, "OK"
    except Exception as e:
        db.rollback()
        return False, str(e)

def update_plan_details(db: Session, name, price, spread, speed, click):
    """Редактирование параметров тарифа из админки"""
    try:
        p = get_plan_by_name(db, name)
        if p:
            p.price_str = price
            p.max_spread = spread
            p.refresh_rate = speed
            p.allow_click_links = click
            db.commit()
            return True
        return False
    except:
        db.rollback()
        return False

def delete_plan_db(db: Session, name):
    try:
        db.query(Plan).filter(Plan.name == name).delete()
        db.commit()
        return True
    except:
        db.rollback()
        return False

# --- ИНВАЙТЫ ---
def get_all_invites(db: Session):
    return db.query(Invite).order_by(Invite.id.desc()).all()

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

# --- РЕГИСТРАЦИЯ И ВЕРИФИКАЦИЯ ---
def register_user_with_invite(db: Session, username, password, email, invite_code):
    invite = db.query(Invite).filter(Invite.code == invite_code).first()
    if not invite or not invite.is_active or invite.used_count >= invite.usage_limit:
        return False, "Invalid/Limit Invite"
    if get_user_by_username(db, username): return False, "Username Taken"
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        code = str(random.randint(100000, 999999))
        new_user = User(username=username, email=email, password_hash=hashed, verification_code=code)
        db.add(new_user)
        db.flush()
        send_verification_email(email, code)
        end_date = datetime.utcnow() + timedelta(days=invite.duration_days) if invite.duration_days else None
        new_sub = Subscription(user_id=new_user.id, plan_name=invite.plan_name, end_date=end_date)
        db.add(new_sub)
        invite.used_count += 1
        db.commit()
        return True, "Code sent"
    except Exception as e:
        db.rollback()
        return False, str(e)

# --- СТАТИСТИКА И ЛОГИ ---
def create_activity_log(db: Session, user_id, action, ip_address=None, details=None):
    try:
        db.add(ActivityLog(user_id=user_id, action=action, ip_address=ip_address, details=details))
        db.commit()
    except: db.rollback()

def get_recent_logs(db: Session, limit=50):
    return db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

def get_dashboard_stats(db: Session):
    return (
        db.query(User).count(), 
        db.query(Invite).filter(Invite.is_active == True).count(), 
        db.query(Subscription).filter(Subscription.plan_name == 'WHALE', Subscription.is_active == True).count()
    )