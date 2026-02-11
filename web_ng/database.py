import sqlite3
import hashlib
import os

DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email TEXT,
            subscription TEXT DEFAULT 'FREE',
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"--- DB: Database {DB_NAME} initialized ---")

def hash_password(password):
    """Профессиональное шифрование (Bcrypt)"""
    # Создаем соль и хешируем пароль
    # encode() превращает строку в байты
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8') # Возвращаем как строку для записи в БД

def create_user(username, password, email=""):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        pwd_hash = hash_password(password)
        
        # ЛОГ ДЛЯ ОТЛАДКИ
        print(f"--- REGISTRATION: User={username}, Hash={pwd_hash} ---")
        
        c.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                  (username, pwd_hash, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        print(f"--- REGISTRATION FAILED: User {username} already exists ---")
        return False
    except Exception as e:
        print(f"--- REGISTRATION ERROR: {e} ---")
        return False

def verify_user(username, password):
    """Проверка с использованием bcrypt"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user:
        stored_hash = user[1] # Хеш из базы
        # Bcrypt сам проверяет совпадение
        try:
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                print("--- LOGIN SUCCESS ---")
                return user
        except Exception as e:
            print(f"Auth error: {e}")
            
    print("--- LOGIN FAILED ---")
    return None

def get_user_info(username):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT username, email, subscription, joined_date FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None