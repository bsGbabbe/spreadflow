from nicegui import ui, app
# Импортируем функции работы с базой данных
from crud import authenticate_user, create_activity_log, get_db, register_user_with_invite
import time


def create_auth_routes():
    
    # --- СТРАНИЦА ВХОДА ---
    @ui.page('/login')
    def login_page():
        # Чистый фон
        ui.add_head_html('<style>body { background-color: #f3f4f6; font-family: sans-serif; }</style>')
        
        with ui.card().classes('absolute-center w-96 p-8 shadow-2xl rounded-xl border border-gray-200'):
            # Заголовок
            ui.label('SPREADFLOW AI').classes('text-xl font-black text-center text-green-600 w-full mb-2 tracking-widest')
            ui.label('Доступ к терминалу').classes('text-sm font-medium text-center text-gray-400 w-full mb-6')
            
            # Поля ввода
            username = ui.input('Логин').props('outlined dense').classes('w-full mb-3')
            password = ui.input('Пароль', password=True, password_toggle_button=True).props('outlined dense').classes('w-full mb-6')
            
            def try_login():
                # 1. Открываем соединение с базой
                db = next(get_db())
                
                try:
                    # 2. Проверяем логин и пароль (через bcrypt)
                    user = authenticate_user(db, username.value, password.value)
                    
                    if user:
                        # === УСПЕШНЫЙ ВХОД ===
                        
                        # 3. Записываем данные в сессию браузера
                        app.storage.user['username'] = user.username
                        app.storage.user['role'] = user.role          # <--- ВАЖНО для админки
                        app.storage.user['user_id'] = str(user.id)    # <--- ВАЖНО для профиля и логов
                        
                        # 4. Пишем лог безопасности в БД
                        create_activity_log(db, user.id, "LOGIN", details={"method": "password_auth"})
                        
                        # 5. Уведомление и редирект
                        ui.notify(f'Добро пожаловать, {user.username}!', type='positive')
                        ui.navigate.to('/') # Перенаправляем в терминал
                        
                    else:
                        # === ОШИБКА ВХОДА ===
                        
                        # 6. ЗАЩИТА ОТ ХАКЕРОВ (Anti-Brute Force)
                        # Заставляем систему "уснуть" на 2 секунды.
                        # Человек этого почти не заметит, а скрипт перебора замедлится в тысячи раз.
                        time.sleep(2.0) 
                        
                        ui.notify('Неверный логин или пароль', type='negative')
                        
                except Exception as e:
                    # Если упала сама база данных или другая ошибка
                    ui.notify(f'Ошибка системы: {str(e)}', type='negative')
                    
                finally:
                    # 7. Всегда закрываем соединение, чтобы не положить сервер
                    db.close()

            # Кнопка входа
            ui.button('ВОЙТИ', on_click=try_login).classes('w-full bg-black text-white font-bold mb-4 shadow-none').props('unelevated')
            
            # Ссылка на регистрацию
            with ui.row().classes('w-full justify-center gap-1'):
                ui.label('Нет аккаунта?').classes('text-xs text-gray-400')
                ui.link('Активировать Инвайт', '/register').classes('text-xs text-green-600 font-bold no-underline hover:underline')
            
            # Ссылка домой (на всякий случай)
            ui.link('← На главную', '/').classes('text-xs text-gray-300 mt-4 block text-center no-underline hover:text-gray-500')

   # --- СТРАНИЦА РЕГИСТРАЦИИ ---
    @ui.page('/register')
    def register_page():
        ui.add_head_html('<style>body { background-color: #f3f4f6; font-family: sans-serif; }</style>')
        
        with ui.card().classes('absolute-center w-96 p-8 shadow-2xl rounded-xl border border-gray-200'):
            ui.label('РЕГИСТРАЦИЯ').classes('text-xl font-black text-center text-gray-900 w-full mb-2')
            ui.label('Активация доступа').classes('text-xs font-bold text-center text-green-600 w-full mb-6 uppercase tracking-widest')
            
            # Поля ввода
            invite_code = ui.input('Инвайт-код (Обязательно)').props('outlined dense').classes('w-full mb-3')
            new_username = ui.input('Придумайте Логин').props('outlined dense').classes('w-full mb-3')
            new_email = ui.input('Email').props('outlined dense').classes('w-full mb-3')
            new_password = ui.input('Пароль', password=True).props('outlined dense').classes('w-full mb-6')
            
            def try_register():
                # Валидация заполнения
                if not invite_code.value or not new_username.value or not new_password.value:
                    ui.notify('Заполните все обязательные поля!', type='warning')
                    return
                
                # Подключение к БД
                db = next(get_db())
                try:
                    # 1. Попытка регистрации пользователя
                    success, message_or_user = register_user_with_invite(
                        db, 
                        new_username.value, 
                        new_password.value, 
                        new_email.value, 
                        invite_code.value
                    )
                    
                    if success:
                        # 2. БЕЗОПАСНОЕ ЛОГИРОВАНИЕ
                        # message_or_user в случае успеха содержит объект созданного пользователя
                        new_user = message_or_user
                        
                        try:
                            # Получаем IP клиента из контекста NiceGUI
                            client_ip = ui.context.client.environ.get('REMOTE_ADDR', '0.0.0.0')
                            
                            create_activity_log(
                                db, 
                                new_user.id, 
                                "REGISTER", 
                                ip_address=str(client_ip), # Принудительно в строку
                                details={"invite": str(invite_code.value)} # Детали как словарь для JSON поля
                            )
                            db.commit() # Фиксируем лог
                        except Exception as log_err:
                            db.rollback() # Сбрасываем только транзакцию лога, если он упал
                            print(f"Log Error: {log_err}")

                        ui.notify('Регистрация успешна!', type='positive')
                        ui.timer(1.0, lambda: ui.navigate.to('/login'))
                    else:
                        # В случае ошибки success=False, message_or_user содержит текст ошибки
                        ui.notify(str(message_or_user), type='negative')
                        
                except Exception as e:
                    ui.notify(f'Ошибка регистрации: {str(e)}', type='negative')
                finally:
                    db.close()

            # Кнопка регистрации
            ui.button('СОЗДАТЬ АККАУНТ', on_click=try_register).classes('w-full bg-green-600 text-white font-bold mb-4 shadow-none').props('unelevated')
            
            # Ссылка назад на вход
            with ui.row().classes('w-full justify-center'):
                ui.link('Уже есть аккаунт? Войти', '/login').classes('text-xs text-gray-500 hover:text-black font-medium')