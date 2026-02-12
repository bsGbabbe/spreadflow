from nicegui import ui, app
from crud import authenticate_user, create_activity_log, get_db, register_user_with_invite, verify_user_code
import time

def create_auth_routes():
    
    # --- ЛОГИН ---
    @ui.page('/login')
    def login_page():
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
                        ui.notify('Email not verified!', color='orange')
                        # Можно перекинуть на страницу верификации, если она есть, или попросить связаться с админом
                        return

                    if user:
                        app.storage.user['username'] = user.username
                        app.storage.user['role'] = user.role
                        app.storage.user['user_info'] = {'role': user.role, 'username': user.username, 'id': str(user.id)} # Совместимость
                        app.storage.user['user_id'] = str(user.id)
                        create_activity_log(db, user.id, "LOGIN")
                        ui.navigate.to('/')
                    else:
                        time.sleep(1.0)
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
        
        # Используем stepper (шаги)
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
                    code_input = ui.input('Enter 6-digit Code').props('outlined dense mask="######"').classes('w-full text-center text-lg tracking-widest')
                    
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