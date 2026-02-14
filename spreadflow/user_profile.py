from nicegui import ui, app
from crud import get_db, get_user_by_username, get_user_plan, authenticate_user, update_user_password, get_user_active_sub
import auth

def create_profile_route():
    @ui.page('/profile')
    def profile_page():
        # === ИСПРАВЛЕНИЕ: Берем данные из user_info ===
        user_info = app.storage.user.get('user_info')
        if not user_info:
            ui.navigate.to('/login')
            return
            
        username = user_info.get('username')
        if not username:
             ui.navigate.to('/login')
             return

        # 2. Загрузка данных из Postgres
        db = next(get_db())
        try:
            user = get_user_by_username(db, username)
            if not user:
                app.storage.user.clear()
                ui.navigate.to('/login')
                return
            
            # Получаем реальный план подписки
            sub = get_user_active_sub(db, user.id)
            plan_name = sub.plan_name if sub else "FREE"
            
            # Данные для отображения
            email_show = user.email
            date_show = user.created_at.strftime("%Y-%m-%d")
            role_show = user.role.upper() # ADMIN или USER
            last_login_show = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'N/A'

        finally:
            db.close()

        # --- ДАЛЬШЕ ИДЕТ ДИЗАЙН (CSS) ---
        ui.add_head_html('''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Roboto+Mono:wght@500;700&display=swap');
            body { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
            .profile-card { background: white; border: 1px solid #e5e7eb; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
            .label-gray { color: #6b7280; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
            .value-text { color: #111827; font-size: 16px; font-weight: 600; }
            .section-title { font-size: 18px; font-weight: 800; color: #111827; margin-bottom: 16px; }
        </style>
        ''')

        # --- HEADER ---
        with ui.header().classes('bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('arrow_back', color='black').classes('cursor-pointer hover:bg-gray-100 rounded-full p-1').on('click', lambda: ui.navigate.to('/'))
                ui.label('Назад в терминал').classes('text-sm font-bold text-gray-500 cursor-pointer').on('click', lambda: ui.navigate.to('/'))
            ui.label('НАСТРОЙКИ ПРОФИЛЯ').classes('text-lg font-black text-gray-900 tracking-tight')
            ui.element('div').classes('w-24') 

        # --- CONTENT ---
        with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-6'):
            
            # Карточка Юзера
            with ui.row().classes('profile-card w-full items-center gap-6'):
                with ui.element('div').classes('relative'):
                    ui.avatar(icon='person', color='gray-200', text_color='gray-600').props('size=100px font-size=50px')
                    ui.element('div').classes('absolute bottom-1 right-1 w-6 h-6 bg-green-500 border-4 border-white rounded-full')
                
                with ui.column().classes('gap-1'):
                    with ui.row().classes('items-center gap-3'):
                        ui.label(user.username).classes('text-2xl font-black text-gray-900')
                        
                        # Бейдж Роли
                        if role_show == 'ADMIN':
                            ui.label('ADMIN').classes('bg-red-600 text-white px-2 py-0.5 rounded text-xs font-bold')
                        
                        # Бейдж Тарифа
                        ui.label(plan_name).classes('bg-black text-white px-2 py-0.5 rounded text-xs font-bold')
                    
                    ui.label(email_show).classes('text-gray-400 font-medium')
                ui.space()

            # Детали
            with ui.row().classes('w-full gap-6'):
                # Колонка 1: Личные данные
                with ui.column().classes('profile-card flex-1 gap-4'):
                    ui.label('Личные данные').classes('section-title')
                    with ui.column().classes('gap-0'):
                        ui.label('Роль').classes('label-gray')
                        ui.label(role_show).classes('value-text')
                    ui.separator()
                    with ui.column().classes('gap-0'):
                        ui.label('Email').classes('label-gray')
                        ui.label(email_show).classes('value-text')
                    ui.separator()
                    with ui.column().classes('gap-0'):
                        ui.label('Дата регистрации').classes('label-gray')
                        ui.label(date_show).classes('value-text')

                # Колонка 2: Подписка + Безопасность + ПОДДЕРЖКА
                with ui.column().classes('flex-1 gap-6'):
                    
                    # Подписка
                    with ui.column().classes('profile-card w-full gap-4 bg-gray-50'):
                        ui.label('Ваша подписка').classes('section-title')
                        with ui.row().classes('items-center justify-between w-full'):
                            ui.label('Текущий план').classes('font-medium text-gray-500')
                            ui.label(plan_name).classes('font-black text-green-600 text-lg')
                        progress_val = 1.0 if plan_name == 'WHALE' else 0.5
                        ui.linear_progress(value=progress_val).props('color=green track-color=grey-3 size=10px rounded').classes('my-2')
                        with ui.row().classes('items-center justify-between w-full'):
                            ui.label('Статус:').classes('text-xs font-bold text-gray-400')
                            ui.label('LIFETIME' if plan_name == 'WHALE' else 'Активен').classes('text-sm font-bold text-purple-600' if plan_name == 'WHALE' else 'text-sm font-bold text-gray-800')

                    # Безопасность (Без изменений)
                    with ui.column().classes('profile-card w-full gap-4'):
                        ui.label('Безопасность').classes('section-title')
                        password_dialog = ui.dialog()
                        with password_dialog, ui.card().classes('w-[400px] p-6'):
                            ui.label('Смена пароля').classes('text-xl font-bold mb-4')
                            old_pass = ui.input('Текущий пароль', password=True).classes('w-full')
                            new_pass = ui.input('Новый пароль', password=True).classes('w-full')
                            confirm_pass = ui.input('Подтвердите пароль', password=True).classes('w-full')
                            def save_password():
                                if new_pass.value != confirm_pass.value:
                                    ui.notify('Пароли не совпадают!', type='negative'); return
                                if len(new_pass.value) < 6:
                                    ui.notify('Пароль должен быть не менее 6 символов', type='warning'); return
                                db = next(get_db())
                                try:
                                    if not authenticate_user(db, user.username, old_pass.value):
                                        ui.notify('Неверный текущий пароль', type='negative'); return
                                    ok, msg = update_user_password(db, user.username, new_pass.value)
                                    if ok: ui.notify(msg, type='positive'); password_dialog.close()
                                    else: ui.notify(msg, type='negative')
                                finally: db.close()
                            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                                ui.button('Отмена', on_click=password_dialog.close).props('flat color=grey')
                                ui.button('Сохранить', on_click=save_password).classes('bg-slate-900 text-white')
                        ui.button('Сменить пароль', icon='lock', on_click=password_dialog.open).props('outline color=slate w-full')
                        ui.label(f'Последний вход: {last_login_show}').classes('text-xs text-gray-400 text-center w-full mt-1')

                    # === НОВАЯ СЕКЦИЯ: ПОДДЕРЖКА ===
                    with ui.column().classes('profile-card w-full gap-4 border-l-4 border-blue-500'):
                        ui.label('Поддержка и Жалобы').classes('section-title')
                        ui.label('Есть вопрос или проблема?').classes('text-sm text-gray-500')
                        
                        support_dialog = ui.dialog()
                        with support_dialog, ui.card().classes('w-[500px] p-6'):
                            ui.label('Новое обращение').classes('text-xl font-bold mb-4')
                            
                            s_subj = ui.input('Тема обращения').props('outlined dense').classes('w-full mb-2')
                            s_msg = ui.textarea('Опишите проблему или жалобу').props('outlined dense').classes('w-full mb-2')
                            s_contact = ui.input('Telegram/Email для связи').props('outlined dense').classes('w-full mb-6')
                            
                            def send_ticket():
                                if not s_subj.value or not s_msg.value:
                                    ui.notify('Заполните тему и сообщение', type='warning'); return
                                
                                db = next(get_db())
                                try:
                                    ok, msg = create_support_ticket(db, user.id, s_subj.value, s_msg.value, s_contact.value)
                                    if ok:
                                        ui.notify('Ваше обращение отправлено!', type='positive')
                                        support_dialog.close()
                                    else:
                                        ui.notify(f'Ошибка: {msg}', type='negative')
                                finally:
                                    db.close()

                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Отмена', on_click=support_dialog.close).props('flat')
                                ui.button('Отправить', on_click=send_ticket).classes('bg-blue-600 text-white')

                        ui.button('Написать в поддержку', icon='support_agent', on_click=support_dialog.open).classes('bg-slate-900 text-white w-full shadow-lg')

            # Выход
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/login')

            with ui.row().classes('w-full justify-center py-6'):
                ui.button('Выйти из аккаунта', icon='logout', on_click=logout).props('flat color=red')