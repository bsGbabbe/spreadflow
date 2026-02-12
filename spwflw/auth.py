from nicegui import ui, app
from fastapi.responses import RedirectResponse
from crud import authenticate_user, create_activity_log, get_db, register_user_with_invite, verify_user_code
import time

# === ВОТ ЭТОГО НЕ ХВАТАЛО ===
class CurrentUser:
    """Обертка для пользователя"""
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
    ui.navigate.to('/login')
# ============================

def create_auth_routes():
    
    # --- ЛОГИН ---
    @ui.page('/login')
    def login_page():
        if app.storage.user.get('user_info'):
            return RedirectResponse('/')

        ui.add_head_html('<style>body { background-color: #f3f4f6; font-family: sans-serif; }</style>')
        with ui.card().classes('absolute-center w-96 p-8 shadow-2xl rounded-xl border border-gray-200'):
            ui.label('SPREADFLOW AI').classes('text-xl font-black text-center text-green-600 w-full mb-8 tracking-widest')
            
            username = ui.input('Login').props('outlined dense').classes('w-full mb-3')
            password = ui.input('Password', password=True).props('outlined dense').classes('w-full mb-6')
            
            def try_login():
                db = next(get_db())
                try:
                    user = authenticate_user(db, username.value, password.value)
                    
                    if user == "unverified":
                        ui.notify('Email not verified! Please register again to get code.', color='orange')
                        return

                    if user:
                        app.storage.user['user_info'] = {
                            'id': str(user.id),
                            'username': user.username,
                            'role': user.role,
                            'email': user.email
                        }
                        create_activity_log(db, user.id, "LOGIN")
                        ui.navigate.to('/')
                    else:
                        time.sleep(1.0)
                        ui.notify('Invalid login or password', type='negative')
                finally:
                    db.close()

            ui.button('LOG IN', on_click=try_login).classes('w-full bg-black text-white font-bold mb-4 shadow-none')
            with ui.row().classes('w-full justify-center'):
                ui.link('Create Account', '/register').classes('text-xs text-green-600 font-bold no-underline')

    # --- РЕГИСТРАЦИЯ (С КОДОМ) ---
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
                                stepper.next() # АВТОМАТИЧЕСКИ ПЕРЕХОДИМ К ВВОДУ КОДА
                            else:
                                ui.notify(msg, type='negative')

                        ui.button('NEXT', on_click=do_reg).classes('bg-black text-white w-full')

                # ШАГ 2: ВВОД КОДА
                with ui.step('Verify Email'):
                    ui.label('Check your email for 6-digit code').classes('text-xs text-gray-500 mb-2')
                    code_input = ui.input('Enter Code').props('outlined dense mask="######"').classes('w-full text-center text-lg tracking-widest mb-4')
                    
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

                        ui.button('VERIFY & FINISH', on_click=do_verify).classes('bg-green-600 text-white w-full')
            
            with ui.row().classes('w-full justify-center mt-4'):
                ui.link('Back to Login', '/login').classes('text-xs text-gray-500')