from nicegui import ui, app
from crud import (
    get_db, get_dashboard_stats, get_all_users, search_users_db, 
    get_all_invites, create_invite_db, get_recent_logs,
    get_all_plans, update_plan_details, create_new_plan, delete_plan_db,
    get_user_active_sub, update_user_subscription_settings, delete_invite_db,
    get_all_tickets, update_ticket_status, delete_ticket_db,
    update_user_role # <--- Импортируем функцию смены роли
)
from logger import log
# === ДОБАВЛЕНО: Импорт моделей для удаления юзера ===
from models import User, Subscription, ActivityLog, Payment, AdminNote, SupportTicket

def create_admin_routes():
    @ui.page('/admin')
    def admin_dashboard():
        # --- ДИАГНОСТИКА СЕССИИ ---
        current_user = app.storage.user.get('username', 'Unknown')
        current_role = app.storage.user.get('role', 'No Role')
        user_id = app.storage.user.get('user_id', 'No ID')
        
        log.info(f"ADMIN ACCESS ATTEMPT: User='{current_user}', Role='{current_role}', ID='{user_id}'")

        # --- БЕЗОПАСНОСТЬ: Разрешаем вход админу и модератору ---
        if current_role not in ['admin', 'moderator']:
            log.error(f"ACCESS DENIED: User '{current_user}' tried to enter Admin but role is '{current_role}'")
            ui.navigate.to('/')
            return

        log.info(f"ACCESS GRANTED: {current_role.upper()} '{current_user}' entered the dashboard.")

        # --- СТИЛИ ---
        ui.add_head_html('''
        <style>
            body { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
            .admin-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            .pricing-card-admin { 
                border: 1px solid #e2e8f0; border-radius: 16px; background: white;
                transition: transform 0.2s; display: flex; flex-direction: column;
            }
            .pricing-card-admin:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }
            .feature-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #f3f4f6; color: #4b5563; }
        </style>
        ''')

        # Загрузка статистики
        db = next(get_db())
        try:
            stats = get_dashboard_stats(db)
        finally:
            db.close()

        # --- HEADER ---
        with ui.header().classes('bg-slate-900 text-white px-8 py-4 flex justify-between items-center shadow-lg'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('admin_panel_settings', size='md', color='blue-400')
                ui.label('GOD MODE').classes('font-black tracking-widest text-lg')
                if current_role == 'moderator':
                    ui.badge('MODERATOR', color='green').classes('text-xs')
            ui.button('EXIT', icon='logout', on_click=lambda: ui.navigate.to('/')).props('flat color=white dense')

        # --- CONTENT ---
        with ui.column().classes('w-full p-8 max-w-7xl mx-auto gap-8'):
            
            # TABS
            with ui.tabs().classes('w-full bg-white rounded-t-xl text-slate-900 border-b') as tabs:
                t_users = ui.tab('Пользователи', icon='group')
                t_plans = ui.tab('Тарифы (Магазин)', icon='store')
                t_invites = ui.tab('Инвайты', icon='vpn_key')
                t_support = ui.tab('Поддержка', icon='headset_mic') 
                t_logs = ui.tab('Логи', icon='history')

            with ui.tab_panels(tabs, value=t_users).classes('w-full bg-white rounded-b-xl p-6 shadow-sm'):
                
                # ==============================================================================
                # TAB 1: USERS
                # ==============================================================================
                with ui.tab_panel(t_users):
                    ui.label('Управление Пользователями').classes('text-xl font-bold mb-4')

                    # --- ДИАЛОГ РЕДАКТИРОВАНИЯ ЮЗЕРА ---
                    user_edit_dialog = ui.dialog()
                    
                    def open_user_edit(user_id, username):
                        user_edit_dialog.clear()
                        db = next(get_db())
                        try:
                            # Получаем юзера (для роли) и подписку
                            user_obj = db.query(User).filter(User.id == user_id).first()
                            sub = get_user_active_sub(db, user_id)
                            
                            current_plan = sub.plan_name if sub else 'FREE'
                            current_role_val = user_obj.role if user_obj else 'user'
                            overrides = sub.custom_overrides if (sub and sub.custom_overrides) else {}
                        finally:
                            db.close()

                        with user_edit_dialog, ui.card().classes('w-[500px] p-6'):
                            with ui.row().classes('justify-between items-center w-full mb-4'):
                                ui.label(f'Настройки: {username}').classes('text-lg font-bold')
                                ui.icon('settings', color='gray')
                            
                            # --- ВЫБОР РОЛИ (НОВОЕ) ---
                            ui.label('Роль (Доступ)').classes('text-xs text-gray-400 font-bold uppercase')
                            role_select = ui.select(['user', 'moderator', 'admin'], value=current_role_val).classes('w-full mb-4')
                            
                            ui.separator().classes('mb-4')

                            # 1. Основной тариф
                            ui.label('Базовый Тариф').classes('text-xs text-gray-400 uppercase font-bold')
                            plan_select = ui.select(['FREE', 'START', 'PRO', 'WHALE'], value=current_plan).classes('w-full mb-6')
                            
                            ui.separator().classes('mb-4')
                            
                            # 2. Индивидуальные исключения (Overrides)
                            ui.label('Персональные исключения (Overrides)').classes('text-sm font-bold text-green-600 uppercase mb-2')
                            ui.label('Заполните поля, чтобы переопределить настройки тарифа.').classes('text-xs text-gray-400 mb-4 leading-tight')

                            with ui.grid(columns=2).classes('gap-4 w-full mb-4'):
                                ov_spread = ui.number('Личный Спред (%)', value=overrides.get('max_spread')).classes('w-full')
                                ov_speed = ui.number('Личная Скорость (сек)', value=overrides.get('refresh_rate')).classes('w-full')
                                # Новые поля
                                ov_max_pairs = ui.number('Лимит связок (кол-во)', value=overrides.get('max_pairs'), placeholder="0 = без лимита").classes('w-full')
                                ov_blocked = ui.input('Блок монет (BTC,ETH...)', value=overrides.get('blocked_coins', '')).classes('w-full')
                            
                            ui.label('Персональные доступы:').classes('text-xs text-gray-400 font-bold mb-2')
                            
                            ov_tele = ui.switch('Разрешить Telegram', value=overrides.get('allow_telegram', False))
                            ov_link = ui.switch('Кликабельные ссылки', value=overrides.get('allow_click_links', False))
                            ov_blur = ui.switch('Блюрить скрытое (Hide)', value=overrides.get('blur_hidden', True)) 
                            
                            def save_user_settings():
                                db = next(get_db())
                                try:
                                    # 1. Обновляем роль
                                    update_user_role(db, user_id, role_select.value)

                                    # 2. Обновляем настройки
                                    new_overrides = {}
                                    
                                    if ov_spread.value is not None: new_overrides['max_spread'] = float(ov_spread.value)
                                    if ov_speed.value is not None: new_overrides['refresh_rate'] = int(ov_speed.value)
                                    
                                    if ov_max_pairs.value is not None and ov_max_pairs.value > 0:
                                        new_overrides['max_pairs'] = int(ov_max_pairs.value)
                                    
                                    if ov_blocked.value:
                                        clean_blocked = ",".join([x.strip().upper() for x in ov_blocked.value.split(',') if x.strip()])
                                        new_overrides['blocked_coins'] = clean_blocked

                                    new_overrides['allow_telegram'] = ov_tele.value
                                    new_overrides['allow_click_links'] = ov_link.value
                                    new_overrides['blur_hidden'] = ov_blur.value
                                    
                                    final_overrides = new_overrides if new_overrides else None
                                    
                                    update_user_subscription_settings(db, user_id, plan_select.value, final_overrides)
                                    ui.notify(f'Настройки и роль {username} сохранены!', type='positive')
                                    user_edit_dialog.close()
                                    refresh_users_table()
                                finally:
                                    db.close()

                            ui.button('СОХРАНИТЬ ИЗМЕНЕНИЯ', on_click=save_user_settings).classes('w-full bg-slate-900 text-white mt-4 shadow-lg')
                        
                        user_edit_dialog.open()

                    # --- ДИАЛОГ УДАЛЕНИЯ ЮЗЕРА ---
                    delete_confirm_dialog = ui.dialog()
                    user_to_delete_data = {'id': None, 'name': None}

                    def open_delete_confirm(u_row):
                        user_to_delete_data['id'] = u_row['user_id']
                        user_to_delete_data['name'] = u_row['username']
                        delete_lbl.set_text(f"Вы точно хотите удалить {u_row['username']}? Это действие необратимо.")
                        delete_confirm_dialog.open()

                    def perform_delete_user():
                        uid = user_to_delete_data['id']
                        if not uid: return
                        
                        db = next(get_db())
                        try:
                            # Удаляем связанные данные (каскадно вручную, для надежности)
                            db.query(Subscription).filter(Subscription.user_id == uid).delete()
                            db.query(ActivityLog).filter(ActivityLog.user_id == uid).delete()
                            db.query(Payment).filter(Payment.user_id == uid).delete()
                            db.query(AdminNote).filter(AdminNote.target_user_id == uid).delete()
                            db.query(SupportTicket).filter(SupportTicket.user_id == uid).delete()
                            
                            # Удаляем самого юзера
                            db.query(User).filter(User.id == uid).delete()
                            db.commit()
                            
                            ui.notify(f"Пользователь {user_to_delete_data['name']} удален", type='positive')
                            refresh_users_table()
                            delete_confirm_dialog.close()
                        except Exception as e:
                            db.rollback()
                            log.error(f"Error deleting user: {e}")
                            ui.notify(f"Ошибка удаления: {e}", type='negative')
                        finally:
                            db.close()

                    with delete_confirm_dialog, ui.card():
                        ui.label('Удаление пользователя').classes('text-lg font-bold text-red-600')
                        delete_lbl = ui.label('...')
                        with ui.row().classes('w-full justify-end mt-4'):
                            ui.button('Отмена', on_click=delete_confirm_dialog.close).props('flat')
                            ui.button('УДАЛИТЬ', on_click=perform_delete_user).classes('bg-red-600 text-white')

                    # --- ТАБЛИЦА ЮЗЕРОВ ---
                    cols = [
                        {'name': 'username', 'label': 'LOGIN', 'field': 'username', 'align': 'left'},
                        {'name': 'role', 'label': 'ROLE', 'field': 'role', 'align': 'center'}, # Новая колонка
                        {'name': 'plan', 'label': 'PLAN', 'field': 'plan', 'align': 'center'},
                        {'name': 'status', 'label': 'TYPE', 'field': 'status', 'align': 'left'},
                        {'name': 'created', 'label': 'CREATED', 'field': 'created', 'align': 'right'},
                        {'name': 'actions', 'label': 'ACTIONS', 'field': 'actions', 'align': 'center'},
                    ]
                    
                    users_table = ui.table(columns=cols, rows=[], pagination=10).classes('w-full')
                    
                    def refresh_users_table():
                        db = next(get_db())
                        try:
                            rows = []
                            for u in get_all_users(db):
                                sub = get_user_active_sub(db, u.id)
                                p_name = sub.plan_name if sub else 'FREE'
                                status_text = "Standard"
                                if sub and sub.custom_overrides:
                                    status_text = "⚡ CUSTOM"
                                
                                rows.append({
                                    'username': u.username,
                                    'role': u.role.upper(), # Роль
                                    'plan': p_name,
                                    'status': status_text,
                                    'created': u.created_at.strftime("%Y-%m-%d"),
                                    'user_id': str(u.id) 
                                })
                            users_table.rows = rows
                        finally:
                            db.close()
                    
                    # Слот для роли
                    users_table.add_slot('body-cell-role', '''
                        <q-td :props="props">
                            <q-badge :color="props.value == 'ADMIN' ? 'red' : (props.value == 'MODERATOR' ? 'green' : 'grey')">
                                {{ props.value }}
                            </q-badge>
                        </q-td>
                    ''')

                    users_table.add_slot('body-cell-plan', '''
                        <q-td :props="props">
                            <q-badge :color="props.value == 'WHALE' ? 'purple' : (props.value == 'PRO' ? 'green' : (props.value == 'START' ? 'blue' : 'grey'))">
                                {{ props.value }}
                            </q-badge>
                        </q-td>
                    ''')
                    
                    users_table.add_slot('body-cell-status', '''
                        <q-td :props="props">
                            <div v-if="props.value.includes('CUSTOM')" class="text-amber-600 font-bold text-xs">{{ props.value }}</div>
                            <div v-else class="text-gray-400 text-xs">{{ props.value }}</div>
                        </q-td>
                    ''')
                    
                    users_table.add_slot('body-cell-actions', r'''
                        <q-td :props="props">
                            <q-btn icon="edit" size="sm" flat dense color="blue" 
                                @click="$parent.$emit('edit_user', props.row)" class="mr-2" />
                            <q-btn icon="delete" size="sm" flat dense color="red" 
                                @click="$parent.$emit('delete_req', props.row)" />
                        </q-td>
                    ''')
                    users_table.on('edit_user', lambda e: open_user_edit(e.args['user_id'], e.args['username']))
                    users_table.on('delete_req', lambda e: open_delete_confirm(e.args))

                    refresh_users_table()
                    ui.button('Обновить список', icon='refresh', on_click=refresh_users_table).props('flat dense')


                # ==============================================================================
                # TAB 2: PLANS
                # ==============================================================================
                with ui.tab_panel(t_plans):
                    with ui.row().classes('w-full justify-between items-center mb-6'):
                        ui.label('Конструктор Тарифов').classes('text-xl font-bold')
                        
                        with ui.dialog() as create_diag, ui.card():
                            ui.label('Новый Тариф').classes('font-bold mb-2')
                            n_name = ui.input('Название (код)', placeholder="VIP")
                            n_price = ui.input('Цена', placeholder="$99")
                            n_spread = ui.number('Макс Спред (%)', value=5)
                            n_speed = ui.number('Скорость (сек)', value=5)
                            n_color = ui.select(['gray', 'blue', 'green', 'purple', 'red', 'amber'], value='gray')
                            
                            def do_create():
                                db = next(get_db())
                                try:
                                    ok, msg = create_new_plan(db, n_name.value, n_price.value, int(n_spread.value), int(n_speed.value), n_color.value)
                                    if ok: 
                                        ui.notify('Тариф создан!')
                                        create_diag.close()
                                        load_plans_ui()
                                    else: ui.notify(msg, type='negative')
                                finally:
                                    db.close()
                                
                            ui.button('СОЗДАТЬ', on_click=do_create).classes('bg-black text-white w-full mt-2')
                        
                        ui.button('ДОБАВИТЬ ТАРИФ', icon='add', on_click=create_diag.open).props('unelevated color=black')

                    plans_container = ui.row().classes('w-full gap-6 items-stretch wrap')

                    edit_plan_dialog = ui.dialog()
                    
                    def open_plan_edit(p):
                        edit_plan_dialog.clear()
                        current_features = list(p.description_features) if p.description_features else []
                        
                        with edit_plan_dialog, ui.card().classes('w-[600px] p-0 gap-0'):
                            with ui.row().classes(f'w-full bg-{p.css_color}-600 p-4 justify-between items-center text-white rounded-t'):
                                ui.label(f'EDITING: {p.name}').classes('font-bold text-lg')
                                ui.icon('edit', color='white')

                            with ui.column().classes('p-6 gap-4 w-full h-[70vh] scroll'):
                                ui.label('Витрина').classes('text-xs text-gray-400 font-bold uppercase')
                                with ui.row().classes('w-full gap-4'):
                                    ep_price = ui.input('Цена', value=p.price_str).classes('flex-1')
                                    ep_period = ui.input('Период', value=p.period_str).classes('flex-1')
                                
                                with ui.row().classes('w-full gap-4 items-center'):
                                    ep_color = ui.select(['gray', 'blue', 'green', 'purple', 'red', 'amber', 'indigo'], value=p.css_color, label='Цвет темы').classes('flex-1')
                                    ep_public = ui.switch('Public', value=p.is_public).props('color=green')
                                
                                ui.separator()
                                ui.label('Лимиты').classes('text-xs text-gray-400 font-bold uppercase')
                                with ui.row().classes('w-full gap-4'):
                                    ep_spread = ui.number('Макс Спред', value=p.max_spread).classes('flex-1')
                                    ep_speed = ui.number('Скорость', value=p.refresh_rate).classes('flex-1')

                                ui.label('Права').classes('text-xs text-gray-400 font-bold uppercase')
                                with ui.row().classes('w-full gap-4 justify-between'):
                                    ep_tele = ui.checkbox('Telegram', value=p.allow_telegram)
                                    ep_click = ui.checkbox('Links', value=p.allow_click_links)
                                    ep_blur = ui.checkbox('Blur', value=p.blur_hidden)

                                ui.separator()
                                features_container = ui.column().classes('w-full gap-2')

                                def render_features():
                                    features_container.clear()
                                    with features_container:
                                        for i, feat in enumerate(current_features):
                                            with ui.row().classes('w-full items-center gap-2'):
                                                ui.icon('check', color='green').classes('text-xs')
                                                f_inp = ui.input(value=feat).props('dense borderless').classes('flex-1 h-8')
                                                f_inp.on('change', lambda e, idx=i: update_feat_text(idx, e.value))
                                                ui.button(icon='close', on_click=lambda _, idx=i: remove_feat(idx)).props('flat dense round color=red size=sm')
                                
                                def update_feat_text(idx, val): current_features[idx] = val
                                def remove_feat(idx):
                                    current_features.pop(idx)
                                    render_features()
                                def add_feat():
                                    current_features.append("Новая фича")
                                    render_features()

                                render_features()
                                ui.button('Добавить пункт', icon='add', on_click=add_feat).props('outline size=sm color=grey').classes('w-full border-dashed')

                                ui.separator()

                                def do_save_plan():
                                    db = next(get_db())
                                    try:
                                        update_plan_details(
                                            db, name=p.name, price=ep_price.value, period=ep_period.value,
                                            color=ep_color.value, is_public=ep_public.value,
                                            spread=int(ep_spread.value), speed=int(ep_speed.value),
                                            blur=ep_blur.value, telegram=ep_tele.value,
                                            click=ep_click.value, features=current_features
                                        )
                                        ui.notify(f'Тариф {p.name} обновлен!', type='positive')
                                        edit_plan_dialog.close()
                                        load_plans_ui()
                                    finally:
                                        db.close()

                                def do_delete_plan():
                                    db = next(get_db())
                                    try:
                                        delete_plan_db(db, p.name)
                                        ui.notify('Тариф удален', type='warning')
                                        edit_plan_dialog.close()
                                        load_plans_ui()
                                    finally:
                                        db.close()

                                with ui.row().classes('w-full gap-4 mt-4'):
                                    ui.button('DELETE', on_click=do_delete_plan).classes('bg-red-100 text-red-600 w-1/3')
                                    ui.button('SAVE', on_click=do_save_plan).classes('flex-1 bg-slate-900 text-white')

                        edit_plan_dialog.open()

                    def load_plans_ui():
                        plans_container.clear()
                        db = next(get_db())
                        try:
                            plans = get_all_plans(db)
                        finally:
                            db.close()
                            
                        with plans_container:
                            for p in plans:
                                opacity_cls = "" if p.is_public else "opacity-60 grayscale"
                                with ui.card().classes(f'pricing-card-admin w-72 p-6 border-t-4 border-{p.css_color}-500 {opacity_cls}'):
                                    with ui.row().classes('justify-between w-full items-start'):
                                        ui.label(p.name).classes(f'text-lg font-black text-{p.css_color}-600 uppercase')
                                        if not p.is_public:
                                            ui.label('HIDDEN').classes('text-[10px] bg-gray-200 px-2 rounded font-bold')
                                    ui.label(p.price_str).classes('text-3xl font-bold mt-2')
                                    with ui.column().classes('gap-1 mb-4'):
                                        ui.label(f"Spread: {p.max_spread}%").classes('text-xs bg-gray-100 px-2 py-1 rounded')
                                    ui.space()
                                    ui.button('EDIT', icon='edit', on_click=lambda _, plan=p: open_plan_edit(plan)).props('flat color=grey w-full')

                    load_plans_ui()

                # ==============================================================================
                # TAB 3: INVITES
                # ==============================================================================
                with ui.tab_panel(t_invites):
                    ui.label('Генератор Инвайтов').classes('text-lg font-bold mb-4')
                    with ui.row().classes('gap-2 items-end mb-4'):
                        ic = ui.input('Код (напр. PRO-FREE)')
                        ip = ui.select(['FREE', 'START', 'PRO', 'WHALE'], value='PRO')
                        il = ui.number('Лимит использований', value=1)
                        def gen_inv():
                            db=next(get_db())
                            try:
                                create_invite_db(db, ic.value, ip.value, int(il.value))
                                ui.notify('Инвайт создан')
                                refresh_invites()
                            finally:
                                db.close()
                        ui.button('Generate', on_click=gen_inv).classes('bg-slate-900 text-white')
                    
                    inv_cols = [
                        {'name': 'code', 'label': 'CODE', 'field': 'code', 'align': 'left'},
                        {'name': 'plan', 'label': 'PLAN', 'field': 'plan', 'align': 'center'},
                        {'name': 'usage', 'label': 'USAGE', 'field': 'usage', 'align': 'center'},
                        {'name': 'status', 'label': 'STATUS', 'field': 'status', 'align': 'center'},
                        {'name': 'actions', 'label': 'DEL', 'field': 'actions', 'align': 'center'},
                    ]
                    inv_table = ui.table(columns=inv_cols, rows=[]).classes('w-full')
                    
                    def delete_invite_handler(inv_id):
                        db = next(get_db())
                        try:
                            delete_invite_db(db, inv_id)
                            ui.notify('Инвайт удален', color='red')
                            refresh_invites()
                        finally:
                            db.close()

                    inv_table.add_slot('body-cell-actions', r'''
                        <q-td :props="props">
                            <q-btn icon="delete" size="sm" flat dense color="red" 
                                @click="$parent.$emit('delete_inv', props.row)" />
                        </q-td>
                    ''')
                    inv_table.on('delete_inv', lambda e: delete_invite_handler(e.args['id']))

                    def refresh_invites():
                        db=next(get_db())
                        try:
                            rows=[]
                            for i in get_all_invites(db):
                                rows.append({
                                    'id': str(i.id),
                                    'code': i.code, 'plan': i.plan_name,
                                    'usage': f"{i.used_count} / {i.usage_limit}",
                                    'status': 'ACTIVE' if i.is_active else 'CLOSED'
                                })
                            inv_table.rows = rows
                        finally:
                            db.close()
                    
                    refresh_invites()

                # ==============================================================================
                # TAB 4: SUPPORT TICKETS
                # ==============================================================================
                with ui.tab_panel(t_support):
                    ui.label('Тикеты пользователей').classes('text-xl font-bold mb-4')
                    
                    t_cols = [
                        {'name': 'date', 'label': 'DATE', 'field': 'date', 'align': 'left'},
                        {'name': 'user', 'label': 'USER', 'field': 'user', 'align': 'left'},
                        {'name': 'subject', 'label': 'SUBJECT', 'field': 'subject', 'align': 'left'},
                        {'name': 'status', 'label': 'STATUS', 'field': 'status', 'align': 'center'},
                        {'name': 'contact', 'label': 'CONTACT', 'field': 'contact', 'align': 'left'},
                        {'name': 'actions', 'label': 'ACTIONS', 'field': 'actions', 'align': 'center'},
                    ]
                    
                    tickets_table = ui.table(columns=t_cols, rows=[], pagination=10).classes('w-full')
                    read_ticket_dialog = ui.dialog()
                    selected_ticket = {'id': None}
                    
                    def open_ticket(row):
                        selected_ticket['id'] = row['id']
                        read_ticket_dialog.clear()
                        with read_ticket_dialog, ui.card().classes('w-[600px] p-6'):
                            with ui.row().classes('justify-between items-start w-full'):
                                ui.label(f"Ticket from {row['user']}").classes('text-lg font-bold')
                                ui.badge(row['status'], color='green' if row['status']=='OPEN' else 'grey')
                            
                            ui.label(f"Тема: {row['subject']}").classes('font-bold mt-2')
                            ui.separator().classes('my-2')
                            ui.markdown(f"**Сообщение:**\n{row['message']}").classes('w-full p-2 bg-gray-50 rounded')
                            
                            if row['contact'] and row['contact'] != '-':
                                ui.label(f"Связь: {row['contact']}").classes('text-sm text-blue-600 mt-2')
                            
                            def change_status(new_st):
                                db = next(get_db())
                                update_ticket_status(db, selected_ticket['id'], new_st)
                                db.close()
                                ui.notify(f'Статус изменен на {new_st}')
                                read_ticket_dialog.close()
                                refresh_tickets()

                            def delete_t():
                                db = next(get_db())
                                delete_ticket_db(db, selected_ticket['id'])
                                db.close()
                                read_ticket_dialog.close()
                                ui.notify('Тикет удален')
                                refresh_tickets()

                            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                                ui.button('Закрыть (Решено)', on_click=lambda: change_status('CLOSED')).props('outline color=green')
                                ui.button('В работу (Open)', on_click=lambda: change_status('OPEN')).props('outline color=blue')
                                ui.button('Удалить', on_click=delete_t).props('flat color=red')
                        
                        read_ticket_dialog.open()

                    def refresh_tickets():
                        db = next(get_db())
                        try:
                            rows = []
                            for t in get_all_tickets(db):
                                rows.append({
                                    'id': str(t.id),
                                    'date': t.created_at.strftime('%Y-%m-%d %H:%M'),
                                    'user': t.user.username,
                                    'subject': t.subject,
                                    'message': t.message,
                                    'status': t.status,
                                    'contact': t.contact_info or '-'
                                })
                            tickets_table.rows = rows
                        finally:
                            db.close()
                            
                    tickets_table.add_slot('body-cell-status', '''
                        <q-td :props="props">
                            <q-badge :color="props.value == 'OPEN' ? 'green' : 'grey'">
                                {{ props.value }}
                            </q-badge>
                        </q-td>
                    ''')
                    tickets_table.add_slot('body-cell-actions', r'''
                        <q-td :props="props">
                            <q-btn icon="visibility" size="sm" flat dense color="blue" 
                                @click="$parent.$emit('open_t', props.row)" />
                        </q-td>
                    ''')
                    tickets_table.on('open_t', lambda e: open_ticket(e.args))
                    refresh_tickets()
                    ui.button('Обновить', icon='refresh', on_click=refresh_tickets).props('flat dense')

                # ==============================================================================
                # TAB 5: LOGS
                # ==============================================================================
                with ui.tab_panel(t_logs):
                     ui.label('Системные логи').classes('text-lg font-bold mb-4')
                     log_cols = [{'name': 'time', 'label': 'TIME', 'field': 'time', 'align': 'left'}, {'name': 'user', 'label': 'USER', 'field': 'user', 'align': 'left'}, {'name': 'action', 'label': 'ACTION', 'field': 'action', 'align': 'left'}]
                     log_table = ui.table(columns=log_cols, rows=[]).classes('w-full')
                     def refresh_logs():
                         db = next(get_db())
                         try:
                             rows = []
                             for l in get_recent_logs(db):
                                 rows.append({
                                     'time': l.timestamp.strftime("%m-%d %H:%M"),
                                     'user': l.user.username if l.user else 'System',
                                     'action': l.action
                                 })
                             log_table.rows = rows
                         finally:
                             db.close()
                     refresh_logs()
                     ui.button('Refresh', icon='refresh', on_click=refresh_logs).props('flat dense')