from nicegui import ui, app
import time
from state import app_state
from config import save_config, DEFAULT_EXCHANGES, DEFAULT_COINS
from crud import get_db, get_user_plan, get_user_by_username
from tariffs import get_user_limits

# --- ГЕНЕРАТОР УМНЫХ ССЫЛОК ---
def get_trade_url(exchange, symbol):
    try:
        base, quote = symbol.split('/')
        base = base.upper()
        quote = quote.upper()
        ex = exchange.lower()

        if ex == 'binance':
            return f"https://www.binance.com/en/trade/{base}_{quote}?type=spot"
        elif ex == 'bybit':
            return f"https://www.bybit.com/trade/spot/{base}/{quote}"
        elif ex == 'okx':
            return f"https://www.okx.com/trade-spot/{base.lower()}-{quote.lower()}"
        elif ex == 'gateio':
            return f"https://www.gate.io/trade/{base}_{quote}"
        elif ex == 'kucoin':
            return f"https://www.kucoin.com/trade/{base}-{quote}"
        elif ex == 'mexc':
            return f"https://www.mexc.com/exchange/{base}_{quote}"
        elif ex == 'htx' or ex == 'huobi':
            return f"https://www.htx.com/trade/{base.lower()}_{quote.lower()}"
        elif ex == 'bitget':
            return f"https://www.bitget.com/spot/{base}{quote}_SPBL"
        elif ex == 'kraken':
            return f"https://pro.kraken.com/app/trade/{base}-{quote}"
        elif ex == 'coinbase':
            return f"https://www.coinbase.com/advanced-trade/{base}-{quote}"
        else:
            return f"https://www.google.com/search?q={ex}+{base}+{quote}+spot"
    except:
        return "https://google.com"

def create_ui():
    # --- CSS СТИЛИ ---
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Roboto+Mono:wght@500;700&display=swap');
        
        body { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
        
        .market-header { font-size: 24px; font-weight: 800; color: #111827; margin-bottom: 15px; letter-spacing: -0.5px; }
        .grid-layout { display: grid; grid-template-columns: 40px 1.5fr 1fr 1fr 1fr 1fr 2fr; align-items: center; }
        .table-header { color: #9ca3af; font-size: 12px; font-weight: 600; text-transform: uppercase; padding: 12px 10px; border-bottom: 1px solid #f3f4f6; }
        
        .table-row { background: white; padding: 16px 10px; border-bottom: 1px solid #f3f4f6; transition: all 0.2s ease; cursor: pointer; }
        .table-row:hover { background: #f9fafb; transform: translateY(-1px); box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
        
        .blur-row { filter: blur(4px); pointer-events: none; opacity: 0.6; }
        .locked-badge { background: #1f2937; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; }

        .coin-name { font-weight: 800; color: #111827; font-size: 14px; }
        .stat-green { color: #10b981; font-weight: 700; font-size: 14px; font-family: 'Roboto Mono', monospace; }
        .stat-price { color: #6b7280; font-weight: 500; font-size: 13px; font-family: 'Roboto Mono', monospace; }
        .route-text { font-weight: 700; color: #374151; font-size: 12px; text-transform: uppercase; }
        
        a.route-link { text-decoration: none !important; border-bottom: none !important; color: #374151; transition: color 0.2s ease; }
        a.route-link:hover { color: #2563eb !important; }

        .calc-box { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 20px; }
        
        input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
    ''')

    # --- ЛОГИКА ---
    def instant_update():
        current_invest = app_state["investment"]
        if current_invest is None: current_invest = 0
        for item in app_state["data"]:
            item['profit'] = (item['spread'] / 100.0) * current_invest
        render_table_rows.refresh()
        if app_state["selected_symbol"]: update_calc()

    # --- ПОЛУЧЕНИЕ ТАРИФА ---
    def get_current_user_plan():
        username = app.storage.user.get('username')
        if not username: return "FREE"
        try:
            db = next(get_db())
            user_obj = get_user_by_username(db, username)
            if user_obj:
                plan = get_user_plan(db, user_obj.id)
                return plan
            return "FREE"
        except:
            return "FREE"
        finally:
            if 'db' in locals(): db.close()

    # --- TOP MENU ---
    with ui.element('div').classes('fixed top-4 right-6 z-50'):
        user = app.storage.user.get('username', None)
        
        if user:
            with ui.button(user, icon='account_circle').props('flat color=grey-9 no-caps'):
                with ui.menu().classes('w-56'):
                    user_role = app.storage.user.get('role', 'user')
                    if user_role == 'admin':
                        with ui.menu_item(on_click=lambda: ui.navigate.to('/admin')):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('admin_panel_settings', size='xs', color='blue')
                                ui.label('АДМИН ПАНЕЛЬ').classes('text-blue-600 font-bold')
                        ui.separator()

                    with ui.menu_item().props('clickable=false'):
                        with ui.column().classes('gap-0'):
                            ui.label(f'{user}').classes('font-bold text-gray-800')
                            ui.label('Active').classes('text-xs text-green-600 font-bold')
                    ui.separator()
                    
                    with ui.menu_item(on_click=lambda: ui.navigate.to('/tariffs')):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('diamond', size='xs', color='purple')
                            ui.label('Тарифы и Оплата').classes('text-purple-700 font-bold')
                    ui.separator()

                    with ui.menu_item(on_click=lambda: ui.navigate.to('/profile')):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('person', size='xs', color='grey')
                            ui.label('Мой профиль')
                    ui.separator()
                    
                    def logout():
                        app.storage.user.clear()
                        ui.navigate.to('/login')
                    with ui.menu_item(on_click=logout):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('logout', size='xs', color='red')
                            ui.label('Выйти').classes('text-red-600 font-bold')
        else:
            ui.button('ВОЙТИ', on_click=lambda: ui.navigate.to('/login')).props('unelevated color=black text-color=white size=sm round font-bold')

    # --- SIDEBAR (ИЗМЕНЕН: УБРАН ПОЛЗУНОК ОБНОВЛЕНИЯ) ---
    with ui.left_drawer(value=True).classes('bg-white p-6 border-r border-gray-100'):
        ui.label("SPREADFLOW").classes('sidebar-title mb-1')
        ui.label("AI ARBITRAGE").classes('text-xs font-bold text-green-600 tracking-widest mb-8')
        
        # --- ИЗМЕНЕНИЕ: СКРЫВАЕМ КНОПКУ ОТ НЕ-АДМИНОВ ---
        user_role = app.storage.user.get('role', 'user') # Получаем роль юзера
        
        btn_start = ui.button('ЗАПУСТИТЬ').classes('w-full mb-8 font-bold shadow-none')
        btn_start.props('unelevated color=black text-color=white rounded')
        
        # Если роль не 'admin' — делаем кнопку невидимой
        if user_role != 'admin':
            btn_start.set_visibility(False)
        # -----------------------------------------------

        def toggle_start():
            if not app_state["selected_exchanges"] or not app_state["selected_coins"]:
                ui.notify('Выберите фильтры!', type='warning')
                return
            app_state["is_running"] = not app_state["is_running"]
            update_start_btn()
            render_table_rows.refresh()
        
        btn_start.on_click(toggle_start)
        btn_start.disable()

        def update_start_btn():
            if not app_state["exchanges_ready"]: return
            btn_start.enable()
            if app_state["is_running"]:
                btn_start.props('color=red-5 text-color=white label="ОСТАНОВИТЬ"')
            else:
                btn_start.props('color=black text-color=white label="ЗАПУСТИТЬ"')

        # Слайдер Инвестиции
        with ui.row().classes('w-full items-center justify-between mb-1'):
            ui.label("Инвестиция ($)").classes('text-xs font-bold text-gray-500 uppercase')
            ui.number(format='%.0f').bind_value(app_state, 'investment').on_value_change(instant_update).classes('w-20').props('dense borderless input-class="text-right font-bold"')
        ui.slider(min=100, max=10000, step=100).bind_value(app_state, 'investment').on_value_change(instant_update).classes('w-full mb-6').props('color=black')

        # Слайдер Мин. Спред
        with ui.row().classes('w-full items-center justify-between mb-1'):
            ui.label("Мин. спред (%)").classes('text-xs font-bold text-gray-500 uppercase')
            ui.number(format='%.2f', step=0.1).bind_value(app_state, 'target_spread').on_value_change(instant_update).classes('w-20').props('dense borderless input-class="text-right font-bold"')
        ui.slider(min=0.0, max=5.0, step=0.1).bind_value(app_state, 'target_spread').on_value_change(instant_update).classes('w-full mb-6').props('color=black')
        
        ui.separator().classes('mb-4 bg-gray-100')

        # --- НОВЫЙ СЛАЙДЕР ОБЪЕМА ---
        with ui.row().classes('w-full items-center justify-between mb-1'):
            ui.label("Мин. Объем 24ч ($)").classes('text-xs font-bold text-gray-500 uppercase')
            # Поле ввода цифрами (шаг 10к, формат без дробей)
            ui.number(format='%.0f', step=10000).bind_value(app_state, 'min_volume').on_value_change(instant_update).classes('w-24').props('dense borderless input-class="text-right font-bold"')
        
        # Сам ползунок (от 0 до 5 млн $)
        ui.slider(min=0, max=5000000, step=10000).bind_value(app_state, 'min_volume').on_value_change(instant_update).classes('w-full mb-6').props('color=black')
        # ---------------------------

        ui.separator().classes('mb-4 bg-gray-100')

        # Фильтры
        with ui.expansion('Фильтр бирж', icon='account_balance').classes('w-full custom-expansion mb-2'):
            with ui.column().classes('pl-2 gap-1'):
                def toggle_ex(name, value):
                    if value and name not in app_state["selected_exchanges"]: app_state["selected_exchanges"].append(name)
                    elif not value and name in app_state["selected_exchanges"]: app_state["selected_exchanges"].remove(name)
                    save_config(app_state["selected_exchanges"], app_state["selected_coins"])
                    instant_update()
                for ex in DEFAULT_EXCHANGES:
                    ui.checkbox(ex.upper(), value=(ex in app_state["selected_exchanges"]), on_change=lambda e, x=ex: toggle_ex(x, e.value)).props('dense size=xs color=black')

        with ui.expansion('Фильтр монет', icon='currency_bitcoin').classes('w-full custom-expansion'):
             with ui.column().classes('pl-2 gap-1'):
                def toggle_cn(name, value):
                    if value and name not in app_state["selected_coins"]: app_state["selected_coins"].append(name)
                    elif not value and name in app_state["selected_coins"]: app_state["selected_coins"].remove(name)
                    save_config(app_state["selected_exchanges"], app_state["selected_coins"])
                    instant_update()
                for coin in DEFAULT_COINS:
                    ui.checkbox(coin, value=(coin in app_state["selected_coins"]), on_change=lambda e, x=coin: toggle_cn(x, e.value)).props('dense size=xs color=black')

    # --- CONTENT ---
    with ui.column().classes('w-full p-8 gap-0'):
        
        # Calculator
        with ui.row().classes('calc-box w-full items-center justify-between') as calc_container:
            calc_container.set_visibility(False)
            with ui.column().classes('gap-0'):
                lbl_pair_name = ui.label("PAIR").classes('text-2xl font-black text-gray-900')
                lbl_pair_prices = ui.label("...").classes('text-sm font-medium text-gray-400')
            with ui.row().classes('items-center gap-4'):
                ui.label("Круги:").classes('font-bold text-gray-500 uppercase text-xs')
                ui.number(min=1, value=1.0, step=1.0).bind_value(app_state, 'loops').on_value_change(instant_update).classes('w-20').props('outlined dense')
            with ui.column().classes('items-end'):
                ui.label("ПРОФИТ").classes('text-xs font-bold text-gray-400')
                lbl_total_profit = ui.label("$0.00").classes('text-3xl font-black text-green-500')

        # Header
        ui.label("Рынок Live").classes('market-header')
        with ui.row().classes('grid-layout w-full'):
            ui.label("") 
            ui.label("МОНЕТА").classes('table-header')
            ui.label("СПРЕД").classes('table-header')
            ui.label("ПРОФИТ").classes('table-header')
            ui.label("ПОКУПКА").classes('table-header')
            ui.label("ПРОДАЖА").classes('table-header')
            ui.label("МАРШРУТ").classes('table-header')

        # --- ТАБЛИЦА ---
        @ui.refreshable
        def render_table_rows():
            if not app_state["data"]:
                with ui.column().classes('w-full items-center justify-center py-20'):
                    if app_state["is_running"]:
                        ui.spinner('dots', size='3em', color='black')
                        ui.label('Анализ рынка...').classes('text-gray-400 mt-4 font-medium animate-pulse')
                    else:
                        ui.icon('rocket', size='3em', color='grey-4')
                        ui.label('Нажмите ЗАПУСТИТЬ в меню').classes('text-gray-400 mt-4 font-medium')
                return

            current_plan = get_current_user_plan()
            limits = get_user_limits(current_plan)

            data = sorted(app_state["data"], key=lambda x: x['spread'], reverse=True)
            
            with ui.column().classes('w-full gap-0'):
                for item in data:
                    if item['symbol'] not in app_state['selected_coins']: continue
                    if item['buy_ex'] not in app_state['selected_exchanges']: continue
                    
                    if item['symbol'] not in limits['coins']: continue 
                    if item['buy_ex'] not in limits['exchanges'] or item['sell_ex'] not in limits['exchanges']: continue 

                    is_locked = item['spread'] > limits['max_spread']
                    sym = item['symbol']
                    
                    if is_locked and limits['blur_hidden']:
                        with ui.row().classes('grid-layout w-full table-row relative-position'):
                            ui.button(icon='lock', color='grey-4').props('flat dense round size=sm disable')
                            with ui.row().classes('items-center gap-2 blur-row'):
                                ui.avatar(icon='currency_bitcoin', color='white', text_color='black').props('size=sm') 
                                ui.label(sym).classes('coin-name')
                            with ui.element('div').classes('absolute-center z-10'):
                                ui.label(f'HIDDEN (> {limits["max_spread"]}%)').classes('locked-badge')
                            ui.label("???").classes('stat-green blur-row')
                            ui.label("???").classes('stat-green blur-row')
                            ui.label("...").classes('stat-price blur-row')
                            ui.label("...").classes('stat-price blur-row')
                            ui.label("LOCKED").classes('route-text blur-row')
                    else:
                        target = app_state['target_spread'] or 0
                        is_profitable = item['spread'] >= target
                        stat_class = 'stat-green' if is_profitable else 'text-red-500 font-bold font-mono text-sm'
                        
                        with ui.row().classes('grid-layout w-full table-row'):
                            def select_pair(s=sym):
                                app_state["selected_symbol"] = s
                                update_calc()
                            
                            ui.button(icon='calculate', on_click=select_pair).props('flat dense round size=sm color=grey-5')
                            with ui.row().classes('items-center gap-2'):
                                ui.avatar(icon='currency_bitcoin', color='white', text_color='black').props('size=sm') 
                                ui.label(sym).classes('coin-name')
                            ui.label(f"{item['spread']:.2f}%").classes(stat_class)
                            ui.label(f"${item['profit']:.2f}").classes(stat_class)
                            ui.label(f"{item['buy_price']}").classes('stat-price')
                            ui.label(f"{item['sell_price']}").classes('stat-price')
                            
                            with ui.row().classes('items-center gap-1'):
                                if current_plan in ['WHALE', 'ADMIN']:
                                    b_ex = item['buy_ex']
                                    s_ex = item['sell_ex']
                                    b_url = get_trade_url(b_ex, sym)
                                    s_url = get_trade_url(s_ex, sym)
                                    ui.link(b_ex.upper(), b_url).classes('route-link route-text').props('target=_blank')
                                    ui.label('→').classes('route-text')
                                    ui.link(s_ex.upper(), s_url).classes('route-link route-text').props('target=_blank')
                                else:
                                    ui.label(f"{item['buy_ex'].upper()} → {item['sell_ex'].upper()}").classes('route-text')

        render_table_rows()

        # Updaters
        def update_calc():
            sym = app_state["selected_symbol"]
            if not sym:
                calc_container.set_visibility(False)
                return
            calc_container.set_visibility(True)
            item = next((x for x in app_state["data"] if x["symbol"] == sym), None)
            if item:
                lbl_pair_name.set_text(sym)
                ex_buy = item['buy_ex'].upper()
                ex_sell = item['sell_ex'].upper()
                price_text = f"Buy on {ex_buy} ({item['buy_price']})  |  Sell on {ex_sell} ({item['sell_price']})"
                lbl_pair_prices.set_text(price_text)
                current_loops = app_state['loops']
                if current_loops is None: current_loops = 1.0
                total = item['profit'] * current_loops
                lbl_total_profit.set_text(f"${total:.2f}")
            else:
                calc_container.set_visibility(False)

        def ui_tick():
            if app_state["exchanges_ready"]: update_start_btn()
            
            plan = get_current_user_plan()
            limits = get_user_limits(plan)
            
            # Обновляем таблицу только если прошло время, указанное в тарифе (refresh_rate)
            time_since_last_render = time.time() - app_state.get('ui_updated_ts', 0)
            
            if time_since_last_render >= limits['refresh_rate']:
                if app_state["last_update_ts"] > app_state.get('ui_updated_ts', 0):
                    render_table_rows.refresh()
                    app_state["ui_updated_ts"] = time.time()
                    if app_state["selected_symbol"]: update_calc()

        ui.timer(0.1, ui_tick)