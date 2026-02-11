from nicegui import ui, app
from crud import (
    get_db, get_dashboard_stats, get_all_users, search_users_db, 
    get_all_invites, create_invite_db, delete_invite_db, # <--- ДОБАВИЛ delete_invite_db
    get_recent_logs, get_all_plans, update_plan_details, 
    create_new_plan, delete_plan_db, get_user_active_sub, 
    update_user_subscription_settings
)

def create_admin_routes():
    @ui.page('/admin')
    def admin_dashboard():
        if app.storage.user.get('role') != 'admin':
            ui.navigate.to('/')
            return

        ui.add_head_html('''
        <style>
            body { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
            .admin-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            
            /* Стили карточек тарифов (как на сайте) */
            .pricing-card-admin { 
                border: 1px solid #e2e8f0; border-radius: 16px; background: white;
                transition: transform 0.2s; display: flex; flex-direction: column;
            }
            .pricing-card-admin:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }
        </style>
        ''')

        db = next(get_db())
        stats = get_dashboard_stats(db)
        db.close()

        # --- HEADER ---
        with ui.header().classes('bg-slate-900 text-white px-8 py-4 flex justify-between items-center shadow-lg'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('admin_panel_settings', size='md', color='blue-400')
                ui.label('GOD MODE').classes('font-black tracking-widest text-lg')
            ui.button('EXIT', icon='logout', on_click=lambda: ui.navigate.to('/')).props('flat color=white dense')

        # --- CONTENT ---
        with ui.column().classes('w-full p-8 max-w-7xl mx-auto gap-8'):
            
            # TABS
            with ui.tabs().classes('w-full bg-white rounded-t-xl text-slate-900 border-b') as tabs:
                t_users = ui.tab('Пользователи', icon='group')
                t_plans = ui.tab('Тарифы (Магазин)', icon='store')
                t_invites = ui.tab('Инвайты', icon='vpn_key')
                t_logs = ui.tab('Логи', icon='history')

            with ui.tab_panels(tabs, value=t_users).classes('w-full bg-white rounded-b-xl p-6 shadow-sm'):
                
                # --- TAB 1: USERS (С РЕДАКТИРОВАНИЕМ) ---
                with ui.tab_panel(t_users):
                    ui.label('Управление Пользователями').classes('text-xl font-bold mb-4')

                    # Диалог редактирования юзера
                    user_edit_dialog = ui.dialog()
                    
                    def open_user_edit(user_id, username):
                        user_edit_dialog.clear()
                        db = next(get_db())
                        
                        # Получаем текущую подписку
                        sub = get_user_active_sub(db, user_id)
                        current_plan = sub.plan_name if sub else 'FREE'
                        
                        # Проверяем оверрайды
                        current_overrides = sub.custom_overrides if (sub and sub.custom_overrides) else {}
                        
                        # --- ИСПРАВЛЕНИЕ НИЖЕ ---
                        # Убираем дефолтное значение '', теперь будет None, если ключа нет
                        custom_spread = current_overrides.get('max_spread')
                        custom_speed = current_overrides.get('refresh_rate')
                        # ------------------------
                        
                        db.close()

                        with user_edit_dialog, ui.card().classes('w-96'):
                            ui.label(f'Настройки: {username}').classes('text-lg font-bold mb-2')
                            
                            # Выбор тарифа
                            ui.label('Основной тариф').classes('text-xs text-gray-400 uppercase font-bold')
                            plan_select = ui.select(['FREE', 'START', 'PRO', 'WHALE'], value=current_plan).classes('w-full mb-4')
                            
                            ui.separator().classes('mb-4')
                            
                            # Индивидуальные настройки
                            ui.label('Индивидуальные настройки (Override)').classes('text-xs text-green-600 uppercase font-bold')
                            ui.label('Если заполнено, эти цифры важнее тарифа').classes('text-xs text-gray-400 mb-2')
                            
                            # Теперь value=None (если нет настройки), и ui.number отработает корректно
                            ov_spread = ui.number('Личный Спред (%)', value=custom_spread).classes('w-full')
                            ov_speed = ui.number('Личная Скорость (сек)', value=custom_speed).classes('w-full')
                            
                            def save_user_settings():
                                db = next(get_db())
                                overrides = {}
                                
                                # Если ввели значения - добавляем в оверрайд
                                # ui.number возвращает float или None, поэтому int() сработает нормально на числах
                                if ov_spread.value is not None: 
                                    overrides['max_spread'] = int(ov_spread.value)
                                if ov_speed.value is not None: 
                                    overrides['refresh_rate'] = int(ov_speed.value)
                                
                                # Если словарь пустой - отправляем None (сброс)
                                final_overrides = overrides if overrides else None
                                
                                update_user_subscription_settings(db, user_id, plan_select.value, final_overrides)
                                db.close()
                                ui.notify(f'Настройки {username} сохранены!', type='positive')
                                user_edit_dialog.close()
                                refresh_users_table()

                            ui.button('СОХРАНИТЬ', on_click=save_user_settings).classes('w-full bg-black text-white mt-4')
                        
                        user_edit_dialog.open()

                    # Таблица
                    # Добавляем колонку "PLAN"
                    cols = [
                        {'name': 'username', 'label': 'LOGIN', 'field': 'username', 'align': 'left'},
                        {'name': 'plan', 'label': 'PLAN', 'field': 'plan', 'align': 'center'}, # <-- НОВАЯ
                        {'name': 'status', 'label': 'STATUS', 'field': 'status', 'align': 'left'},
                        {'name': 'actions', 'label': 'EDIT', 'field': 'actions', 'align': 'center'},
                    ]
                    
                    users_table = ui.table(columns=cols, rows=[], pagination=10).classes('w-full')
                    
                    def refresh_users_table():
                        db = next(get_db())
                        rows = []
                        for u in get_all_users(db):
                            # Получаем подписку для отображения
                            sub = get_user_active_sub(db, u.id)
                            p_name = sub.plan_name if sub else 'FREE'
                            
                            # Если есть оверрайды - добавляем пометку
                            status_text = "Standard"
                            if sub and sub.custom_overrides:
                                status_text = "⚡ CUSTOM"
                            
                            rows.append({
                                'username': u.username,
                                'plan': p_name,
                                'status': status_text,
                                'user_id': str(u.id) # скрытое поле для логики
                            })
                        db.close()
                        users_table.rows = rows
                        
                        # Добавляем слоты для кнопок и статусов
                        users_table.add_slot('body-cell-plan', '''
                            <q-td :props="props">
                                <q-badge :color="props.value == 'WHALE' ? 'purple' : (props.value == 'PRO' ? 'green' : 'grey')">
                                    {{ props.value }}
                                </q-badge>
                            </q-td>
                        ''')
                        
                        # Кнопка редактирования
                        users_table.add_slot('body-cell-actions', r'''
                            <q-td :props="props">
                                <q-btn icon="edit" size="sm" flat dense color="blue" 
                                    @click="$parent.$emit('edit_user', props.row)" />
                            </q-td>
                        ''')
                        # Обработчик нажатия (хитрая магия NiceGUI для слотов)
                        users_table.on('edit_user', lambda e: open_user_edit(e.args['user_id'], e.args['username']))

                    refresh_users_table()
                    ui.button('Обновить список', icon='refresh', on_click=refresh_users_table).props('flat dense')

                # --- TAB 2: PLANS (КАК В МАГАЗИНЕ) ---
                with ui.tab_panel(t_plans):
                    with ui.row().classes('w-full justify-between items-center mb-6'):
                        ui.label('Конструктор Тарифов').classes('text-xl font-bold')
                        # Кнопка создания
                        with ui.dialog() as create_diag, ui.card():
                            ui.label('Новый Тариф').classes('font-bold')
                            n_name = ui.input('Название (напр. VIP)')
                            n_price = ui.input('Цена (текст, напр. $500)')
                            n_spread = ui.number('Макс Спред (%)', value=5)
                            n_speed = ui.number('Скорость (сек)', value=5)
                            n_color = ui.select(['gray', 'blue', 'green', 'purple', 'red'], value='gray')
                            
                            def do_create():
                                db = next(get_db())
                                ok, msg = create_new_plan(db, n_name.value, n_price.value, int(n_spread.value), int(n_speed.value), n_color.value)
                                db.close()
                                if ok: 
                                    ui.notify('Создано!')
                                    create_diag.close()
                                    load_plans_ui()
                                else: ui.notify(msg, type='negative')
                                
                            ui.button('СОЗДАТЬ', on_click=do_create).classes('bg-black text-white w-full')
                        
                        ui.button('ДОБАВИТЬ ТАРИФ', icon='add', on_click=create_diag.open).props('unelevated color=black')

                    plans_container = ui.row().classes('w-full gap-6 items-stretch wrap')

                    # Диалог редактирования тарифа
                    edit_plan_dialog = ui.dialog()
                    
                    def open_plan_edit(p):
                        edit_plan_dialog.clear()
                        with edit_plan_dialog, ui.card().classes('w-80'):
                            ui.label(f'Edit {p.name}').classes('font-bold')
                            e_price = ui.input('Цена', value=p.price_str)
                            e_spread = ui.number('Спред', value=p.max_spread)
                            e_speed = ui.number('Скорость', value=p.refresh_rate)
                            
                            def do_save():
                                db = next(get_db())
                                update_plan_details(db, p.name, e_price.value, int(e_spread.value), int(e_speed.value), p.allow_click_links)
                                db.close()
                                edit_plan_dialog.close()
                                load_plans_ui()
                            
                            def do_delete():
                                db = next(get_db())
                                delete_plan_db(db, p.name)
                                db.close()
                                edit_plan_dialog.close()
                                load_plans_ui()
                                ui.notify('Тариф удален')

                            ui.button('SAVE', on_click=do_save).classes('w-full bg-blue-600 text-white')
                            ui.button('DELETE', on_click=do_delete).classes('w-full bg-red-100 text-red-600 flat mt-2')
                        edit_plan_dialog.open()

                    def load_plans_ui():
                        plans_container.clear()
                        db = next(get_db())
                        plans = get_all_plans(db)
                        db.close()
                        
                        with plans_container:
                            for p in plans:
                                # Карточка 1-в-1 как в tariffs_page, но с кнопкой EDIT
                                with ui.card().classes(f'pricing-card-admin w-72 p-6 border-t-4 border-{p.css_color}-500'):
                                    with ui.row().classes('justify-between w-full'):
                                        ui.label(p.name).classes(f'text-lg font-black text-{p.css_color}-600 uppercase')
                                        ui.button(icon='edit', on_click=lambda _, plan=p: open_plan_edit(plan)).props('flat round dense color=grey')

                                    ui.label(p.price_str).classes('text-3xl font-bold mt-2')
                                    ui.label('/ week').classes('text-xs text-gray-400 font-bold mb-4')
                                    
                                    ui.separator().classes('mb-4')
                                    
                                    ui.label(f"✓ Спреды до {p.max_spread}%").classes('text-sm text-gray-600')
                                    ui.label(f"✓ Обновление {p.refresh_rate}с").classes('text-sm text-gray-600')
                                    if p.allow_click_links:
                                        ui.label(f"✓ Smart Links").classes('text-sm font-bold text-blue-600')

                    load_plans_ui()

                # --- TAB 3: INVITES ---
                with ui.tab_panel(t_invites):
                    ui.label('Управление Инвайтами').classes('text-lg font-bold mb-4')
                    
                    # 1. ФОРМА ГЕНЕРАЦИИ
                    with ui.card().classes('w-full p-4 mb-8 bg-gray-50 border border-gray-200'):
                        ui.label('Создать новый код').classes('text-sm font-bold text-gray-400 uppercase mb-2')
                        with ui.row().classes('w-full items-start gap-4'):
                            ic = ui.input('Код (напр. PRO-2024)').props('outlined dense bg-white').classes('flex-1')
                            ip = ui.select(['START', 'PRO', 'WHALE'], value='PRO', label='Тариф').props('outlined dense bg-white').classes('w-40')
                            il = ui.number('Лимит', value=1).props('outlined dense bg-white').classes('w-24')
                            idys = ui.number('Дней (0=Вечно)', value=30).props('outlined dense bg-white').classes('w-32')
                        
                        def gen_inv():
                            if not ic.value:
                                ui.notify('Введите код!', type='negative')
                                return
                            
                            db = next(get_db())
                            ok, msg = create_invite_db(db, ic.value, ip.value, int(il.value), int(idys.value))
                            db.close()
                            
                            if ok: 
                                ui.notify('Инвайт создан!', type='positive')
                                ic.value = '' # Очистить поле
                                refresh_invites_table() # Обновить таблицу
                            else: 
                                ui.notify(f'Ошибка: {msg}', type='negative')

                        ui.button('СГЕНЕРИРОВАТЬ', on_click=gen_inv).classes('w-full bg-black text-white mt-4 shadow-none')

                    ui.separator().classes('mb-6')

                    # 2. ТАБЛИЦА ИНВАЙТОВ
                    ui.label('Список активных кодов').classes('text-lg font-bold mb-4')

                    # Настройка колонок
                    inv_cols = [
                        {'name': 'code', 'label': 'КОД', 'field': 'code', 'align': 'left', 'sortable': True},
                        {'name': 'plan', 'label': 'ТАРИФ', 'field': 'plan', 'align': 'center', 'sortable': True},
                        {'name': 'duration', 'label': 'СРОК', 'field': 'duration', 'align': 'center'},
                        {'name': 'usage', 'label': 'ИСПОЛЬЗОВАНО', 'field': 'usage', 'align': 'center'},
                        {'name': 'actions', 'label': 'УДАЛИТЬ', 'field': 'actions', 'align': 'center'},
                    ]
                    
                    invites_table = ui.table(columns=inv_cols, rows=[], pagination=10).classes('w-full')

                    def delete_inv(inv_id):
                        db = next(get_db())
                        delete_invite_db(db, inv_id)
                        db.close()
                        ui.notify('Инвайт удален', color='orange')
                        refresh_invites_table()

                    def refresh_invites_table():
                        db = next(get_db())
                        invites = get_all_invites(db)
                        db.close()
                        
                        rows = []
                        for inv in invites:
                            # Красивое отображение срока
                            dur_text = "∞ LIFETIME"
                            if inv.duration_days and inv.duration_days > 0:
                                dur_text = f"{inv.duration_days} дн."
                            
                            # Отображение использования
                            usage_text = f"{inv.used_count} / {inv.usage_limit}"
                            
                            rows.append({
                                'code': inv.code,
                                'plan': inv.plan_name,
                                'duration': dur_text,
                                'usage': usage_text,
                                'id': str(inv.id), # Скрытый ID для удаления
                                'is_lifetime': (inv.duration_days is None or inv.duration_days == 0) # Флаг для цвета
                            })
                        invites_table.rows = rows
                        
                        # --- СЛОТЫ ДЛЯ КРАСОТЫ (NiceGUI/Quasar) ---
                        
                        # Слот для Тарифа (цветные бейджи)
                        invites_table.add_slot('body-cell-plan', '''
                            <q-td :props="props">
                                <q-badge :color="props.value == 'WHALE' ? 'purple' : (props.value == 'PRO' ? 'green' : 'blue')">
                                    {{ props.value }}
                                </q-badge>
                            </q-td>
                        ''')
                        
                        # Слот для Срока (Фиолетовый для вечных, Серый для временных)
                        invites_table.add_slot('body-cell-duration', '''
                            <q-td :props="props">
                                <div v-if="props.row.is_lifetime" class="text-purple-600 font-bold text-xs">
                                    ⚡ LIFETIME
                                </div>
                                <div v-else class="text-gray-500 font-bold text-xs">
                                    {{ props.value }}
                                </div>
                            </q-td>
                        ''')

                        # Слот для Кнопки Удаления
                        invites_table.add_slot('body-cell-actions', r'''
                            <q-td :props="props">
                                <q-btn icon="delete" size="sm" flat dense color="red" 
                                    @click="$parent.$emit('delete_click', props.row.id)" />
                            </q-td>
                        ''')
                        
                        # Привязываем событие удаления
                        invites_table.on('delete_click', lambda e: delete_inv(e.args))

                    # Загружаем данные при открытии вкладки
                    refresh_invites_table()
                    ui.button('ОБНОВИТЬ СПИСОК', icon='refresh', on_click=refresh_invites_table).props('flat dense color=grey')

                # --- TAB 4: LOGS ---
                with ui.tab_panel(t_logs):
                     # (Код логов тот же)
                     pass