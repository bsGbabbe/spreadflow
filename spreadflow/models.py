import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# --- 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ ---
class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False) 
    
    role = Column(String(20), default='user') 
    is_active = Column(Boolean, default=True) 
    
    # Связи
    payments = relationship("Payment", back_populates="user")
    tickets = relationship("SupportTicket", back_populates="user") # <--- НОВОЕ: Связь с тикетами
    
    is_verified = Column(Boolean, default=False) 
    verification_code = Column(String(6), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    logs = relationship("ActivityLog", back_populates="user")
    notes = relationship("AdminNote", back_populates="target_user", foreign_keys="AdminNote.target_user_id")

# --- 2. ТАБЛИЦА АКТИВНОСТИ ---
class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action = Column(String(100), nullable=False) 
    ip_address = Column(INET, nullable=True)     
    user_agent = Column(Text, nullable=True)     
    details = Column(JSON, nullable=True)        
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="logs")

# --- 3. ЗАМЕТКИ АДМИНА ---
class AdminNote(Base):
    __tablename__ = 'admin_notes'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id')) 
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))      
    note_text = Column(Text, nullable=False)     
    flag_color = Column(String(20), default='gray') 
    created_at = Column(DateTime, default=datetime.utcnow)
    target_user = relationship("User", foreign_keys=[target_user_id], back_populates="notes")
    author = relationship("User", foreign_keys=[author_id])

# --- 4. ПОДПИСКИ ---
class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    plan_name = Column(String(50), default='FREE') 
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)     
    is_active = Column(Boolean, default=True)
    custom_overrides = Column(JSON, nullable=True)

# --- 5. ИНВАЙТЫ ---
class Invite(Base):
    __tablename__ = 'invites'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False) 
    plan_name = Column(String(50), default='PRO')          
    is_active = Column(Boolean, default=True)              
    usage_limit = Column(Integer, default=100)
    used_count = Column(Integer, default=0)
    duration_days = Column(Integer, nullable=True)

# --- 6. ТАРИФЫ ---
class Plan(Base):
    __tablename__ = 'plans'
    name = Column(String(50), primary_key=True)
    price_str = Column(String(20), default="$0")
    period_str = Column(String(20), default="/ week")
    description_features = Column(JSON, default=[])
    css_color = Column(String(20), default="gray")
    max_spread = Column(Integer, default=1)
    refresh_rate = Column(Integer, default=30)
    blur_hidden = Column(Boolean, default=True)
    allow_telegram = Column(Boolean, default=False)
    allow_click_links = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)

# --- 7. ПЛАТЕЖИ ---
class Payment(Base):
    __tablename__ = 'payments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    invoice_id = Column(String, unique=True)
    amount_usd = Column(Float)
    currency = Column(String)
    status = Column(String, default="pending")
    plan_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="payments")

# --- 8. ТИКЕТЫ ПОДДЕРЖКИ (НОВОЕ) ---
class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    subject = Column(String(255), nullable=False) # Тема
    message = Column(Text, nullable=False)        # Сообщение
    contact_info = Column(String(255), nullable=True) # Контакт (ТГ/Email)
    status = Column(String(20), default='OPEN')   # OPEN, CLOSED
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="tickets")