from nicegui import ui, app
from crud import authenticate_user, create_activity_log, get_db, register_user_with_invite, verify_user_code, get_user_by_username, resend_verification_code
import time
from models import Subscription
from logger import log

# --- ПОЛУЧЕНИЕ ТЕКУЩЕГО ЮЗЕРА ---
def get_current_user():
    """Возвращает объект пользователя из базы на основе данных сессии"""
    username = app.storage.user.get('username')
    if not username:
        return None
    
    db = next(get_db())
    try:
        user = get_user_by_username(db, username)
        return user
    finally:
        db.close()

# --- ВЫХОД ---
def logout():
    """Очищает сессию и перенаправляет на логин"""
    app.storage.user.clear()
    ui.navigate.to('/login')

def create_auth_routes():
    
    # --- ЛОГИН ---
    @ui.page('/login')
    def login_page():
        ui.add_head_html('<style>body { background-color: #f3f4f6; font-family: sans-serif; }</style>')
        
        # Диалог верификации (скрыт по умолчанию)
        verify_dialog = ui.dialog()
        
        with ui.card().classes('absolute-center w-96 p-8 shadow-2xl rounded-xl border border-gray-200'):
            ui.label('SPREADFLOW AI').classes('text-xl font-black text-center text-green-600 w-full mb-8 tracking-widest')
            
            username = ui.input('Login').props('outlined dense').classes('w-full mb-3')
            password = ui.input('Password', password=True).props('outlined dense').classes('w-full mb-6')
            
            # --- Логика Диалога Верификации ---
            with verify_dialog, ui.card().classes('w-full max-w-sm p-6'):
                ui.label('Email не подтвержден!').classes('text-lg font-bold text-red-600 mb-2')
                ui.label('Введите код из письма, чтобы активировать аккаунт.').classes('text-sm text-gray-500 mb-4')
                
                v_code_input = ui.input('Код из почты').props('outlined dense mask="######" text-center').classes('w-full mb-4 text-lg')
                
                def do_verify_login():
                    db = next(get_db())
                    ok, msg = verify_user_code(db, username.value, v_code_input.value)
                    db.close()
                    if ok:
                        ui.notify('Успешно! Теперь войдите.', type='positive')
                        verify_dialog.close()
                    else:
                        ui.notify(msg, type='negative')

                def do_resend_code():
                    db = next(get_db())
                    ok, msg = resend_verification_code(db, username.value)
                    db.close()
                    if ok:
                        ui.notify(msg, type='positive')
                    else:
                        ui.notify(msg, type='warning')

                ui.button('ПОДТВЕРДИТЬ', on_click=do_verify_login).classes('w-full bg-green-600 text-white mb-2')
                ui.button('Отправить код повторно', on_click=do_resend_code).props('flat dense color=grey').classes('w-full')

            # --- Логика Входа ---
            def try_login():
                db = next(get_db())
                try:
                    user = authenticate_user(db, username.value, password.value)
                    
                    if user == "unverified":
                        # Открываем диалог верификации вместо простого уведомления
                        verify_dialog.open()
                        return

                    if user:
                        app.storage.user['username'] = user.username
                        app.storage.user['role'] = user.role
                        app.storage.user['user_info'] = {'role': user.role, 'username': user.username, 'id': str(user.id)}
                        app.storage.user['user_id'] = str(user.id)
                        
                        log.info(f"AUTH SUCCESS: User {user.username} logged in with role: {user.role}")
                        create_activity_log(db, user.id, "LOGIN")
                        ui.navigate.to('/')
                    else:
                        time.sleep(1.0)
                        log.warning(f"AUTH FAILED: Attempt for username: {username.value}")
                        ui.notify('Invalid login or password', type='negative')
                finally:
                    db.close()

            ui.button('LOG IN', on_click=try_login).classes('w-full bg-black text-white font-bold mb-4 shadow-none')
            with ui.row().classes('w-full justify-center'):
                ui.link('Activate Invite', '/register').classes('text-xs text-green-600 font-bold no-underline')

    # --- РЕГИСТРАЦИЯ + ВЕРИФИКАЦИЯ ---
    @ui.page('/register')
    def register_page():
        ui.add_head_html('<style>body { background-color: #f3f4f6; font-family: sans-serif; }</style>')
        
        with ui.card().classes('absolute-center w-96 p-8 shadow-2xl rounded-xl border border-gray-200'):
            ui.label('REGISTRATION').classes('text-xl font-black text-center text-gray-900 w-full mb-6')
            
            with ui.stepper().props('flat vertical').classes('w-full') as stepper:
                
                # ШАГ 1: ДАННЫЕ
                with ui.step('Details'):
                    invite_code = ui.input('Invite Code').props('outlined dense').classes('w-full mb-2')
                    new_username = ui.input('Username').props('outlined dense').classes('w-full mb-2')
                    new_email = ui.input('Email').props('outlined dense').classes('w-full mb-2')
                    new_password = ui.input('Password', password=True).props('outlined dense').classes('w-full')
                    
                    with ui.stepper_navigation():
                        def do_reg():
                            if not all([invite_code.value, new_username.value, new_email.value, new_password.value]):
                                ui.notify('Fill all fields', color='red'); return
                            
                            db = next(get_db())
                            ok, msg = register_user_with_invite(db, new_username.value, new_password.value, new_email.value, invite_code.value)
                            db.close()
                            
                            if ok:
                                ui.notify(f'Code sent to {new_email.value}', type='positive')
                                stepper.next() # Переход к шагу 2
                            else:
                                ui.notify(msg, type='negative')

                        ui.button('NEXT', on_click=do_reg).classes('bg-black text-white')

                # ШАГ 2: ВЕРИФИКАЦИЯ
                with ui.step('Verify Email'):
                    ui.label('Check your email for code').classes('text-xs text-gray-500 mb-2')
                    code_input = ui.input('Enter 6-digit Code').props('outlined dense mask="######"').classes('w-full text-center text-lg tracking-widest mb-2')
                    
                    with ui.stepper_navigation():
                        def do_verify():
                            db = next(get_db())
                            ok, msg = verify_user_code(db, new_username.value, code_input.value)
                            db.close()
                            
                            if ok:
                                ui.notify('Verified! Login now.', type='positive')
                                ui.navigate.to('/login')
                            else:
                                ui.notify(msg, type='negative')
                        
                        def do_resend_reg():
                            db = next(get_db())
                            ok, msg = resend_verification_code(db, new_username.value)
                            db.close()
                            if ok: ui.notify(msg, type='positive')
                            else: ui.notify(msg, type='warning')

                        with ui.column().classes('w-full gap-2'):
                            ui.button('VERIFY & FINISH', on_click=do_verify).classes('bg-green-600 text-white w-full')
                            ui.button('Resend Code', on_click=do_resend_reg).props('flat dense color=grey').classes('w-full text-xs')
            
            with ui.row().classes('w-full justify-center mt-4'):
                ui.link('Back to Login', '/login').classes('text-xs text-gray-500')