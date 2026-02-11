from nicegui import ui, app
from crud import get_db, get_user_by_username, get_user_plan

def create_profile_route():
    @ui.page('/profile')
    def profile_page():
        # 1. Проверка сессии
        username = app.storage.user.get('username')
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
            plan_name = get_user_plan(db, user.id)
            
            # Данные для отображения
            email_show = user.email
            date_show = user.created_at.strftime("%Y-%m-%d")
            role_show = user.role.upper() # ADMIN или USER

        finally:
            db.close()

        # --- ДАЛЬШЕ ИДЕТ ДИЗАЙН (CSS) ---
        # (Код стилей остается тем же, что и был, меняем только переменные ниже)
        
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
        with ui.column().classes('w-full max-w-3xl mx-auto p-8 gap-6'):
            
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

                with ui.column().classes('profile-card flex-1 gap-4 bg-gray-50'):
                    ui.label('Ваша подписка').classes('section-title')
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label('Текущий план').classes('font-medium text-gray-500')
                        ui.label(plan_name).classes('font-black text-green-600 text-lg')
                    
                    # Если тариф WHALE - полоска полная
                    progress_val = 1.0 if plan_name == 'WHALE' else 0.5
                    ui.linear_progress(value=progress_val).props('color=green track-color=grey-3 size=10px rounded').classes('my-2')
                    
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label('Статус:').classes('text-xs font-bold text-gray-400')
                        if plan_name == 'WHALE':
                             ui.label('LIFETIME').classes('text-sm font-bold text-purple-600')
                        else:
                             ui.label('Активен').classes('text-sm font-bold text-gray-800')

            # Выход
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/login')

            with ui.row().classes('w-full justify-center py-6'):
                ui.button('Выйти из аккаунта', icon='logout', on_click=logout).props('flat color=red')