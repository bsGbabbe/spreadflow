from nicegui import ui, app
from fastapi.responses import RedirectResponse
from models import User
import uuid
import bcrypt  # <--- Для проверки хешей паролей

# Пытаемся импортировать сессию БД
try:
    from db_session import SessionLocal
except ImportError:
    try:
        from init_db import SessionLocal
    except ImportError:
        # Фоллбек для локальных тестов
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        import os
        db_url = os.getenv("DATABASE_URL", "sqlite:///users.db")
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)

# === ВСПОМОГАТЕЛЬНЫЙ КЛАСС ===
class CurrentUser:
    """Обертка для удобного доступа user.username вместо словаря"""
    def __init__(self, user_dict):
        self.id = user_dict.get('id')
        self.username = user_dict.get('username', 'Guest')
        self.role = user_dict.get('role', 'user')
        self.email = user_dict.get('email', '')

def get_current_user():
    """Получает пользователя из сессии"""
    user_data = app.storage.user.get('user_info')
    if user_data:
        return CurrentUser(user_data)
    return None

def logout():
    """Выход"""
    app.storage.user.clear()
    # ИСПРАВЛЕНО: ui.open -> ui.navigate.to
    ui.navigate.to('/login')

def create_auth_routes():
    
    # --- СТРАНИЦА ВХОДА ---
    @ui.page('/login')
    def login_page():
        if app.storage.user.get('user_info'):
            return RedirectResponse('/')

        ui.add_head_html('<style>body { background-color: #f1f5f9; font-family: sans-serif; }</style>')
        
        with ui.card().classes('absolute-center w-full max-w-sm p-8 rounded-xl shadow-lg gap-4'):
            ui.label('SpreadFlow AI').classes('text-2xl font-black text-slate-800 w-full text-center mb-4')
            
            username = ui.input('Username').classes('w-full').props('outlined dense')
            password = ui.input('Password', password=True, password_toggle_button=True).classes('w-full').props('outlined dense')
            
            def try_login():
                session = SessionLocal()
                try:
                    # Ищем пользователя
                    user = session.query(User).filter(User.username == username.value).first()
                    
                    if user:
                        # Проверяем хеш пароля (безопасный вход)
                        input_bytes = password.value.encode('utf-8')
                        hash_bytes = user.password_hash.encode('utf-8')
                        
                        if bcrypt.checkpw(input_bytes, hash_bytes):
                            # Сохраняем сессию
                            app.storage.user['user_info'] = {
                                'id': str(user.id),
                                'username': user.username,
                                'role': user.role,
                                'email': user.email
                            }
                            # ИСПРАВЛЕНО: ui.open -> ui.navigate.to
                            ui.navigate.to('/')
                            return 
                    
                    ui.notify('Invalid username or password', color='red')
                    
                except Exception as e:
                    ui.notify(f'Login error: {e}', color='red')
                finally:
                    session.close()

            ui.button('LOG IN', on_click=try_login).classes('w-full font-bold bg-slate-800 text-white shadow-md')
            
            with ui.row().classes('w-full justify-center mt-2'):
                ui.link('Create account', '/register').classes('text-sm text-slate-500 hover:text-slate-800')

    # --- СТРАНИЦА РЕГИСТРАЦИИ ---
    @ui.page('/register')
    def register_page():
        ui.add_head_html('<style>body { background-color: #f1f5f9; font-family: sans-serif; }</style>')
        
        with ui.card().classes('absolute-center w-full max-w-sm p-8 rounded-xl shadow-lg gap-4'):
            ui.label('Create Account').classes('text-2xl font-black text-slate-800 w-full text-center mb-4')
            
            username = ui.input('Username').classes('w-full').props('outlined dense')
            email = ui.input('Email').classes('w-full').props('outlined dense')
            password = ui.input('Password', password=True).classes('w-full').props('outlined dense')
            
            def try_register():
                if not username.value or not password.value:
                    ui.notify('Fill all fields', color='red')
                    return

                session = SessionLocal()
                try:
                    if session.query(User).filter(User.username == username.value).first():
                        ui.notify('Username already taken', color='red')
                        return

                    # Хешируем пароль при регистрации
                    pwd_bytes = password.value.encode('utf-8')
                    salt = bcrypt.gensalt()
                    hashed_pw = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

                    new_user = User(
                        username=username.value,
                        email=email.value,
                        password_hash=hashed_pw, 
                        role='user',
                        is_active=True
                    )
                    session.add(new_user)
                    session.commit()
                    
                    ui.notify('Account created! Please login.', color='green')
                    # ИСПРАВЛЕНО: ui.open -> ui.navigate.to
                    ui.navigate.to('/login')
                except Exception as e:
                    ui.notify(f'Error: {e}', color='red')
                finally:
                    session.close()

            ui.button('REGISTER', on_click=try_register).classes('w-full font-bold bg-green-600 text-white shadow-md')
            with ui.row().classes('w-full justify-center mt-2'):
                ui.link('Back to Login', '/login').classes('text-sm text-slate-500 hover:text-slate-800')