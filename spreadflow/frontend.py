from nicegui import ui, app
import time
from state import app_state
from config import save_config, DEFAULT_EXCHANGES
from crud import get_db, get_user_plan, get_user_by_username
from tariffs import get_user_limits

# --- ГЕНЕРАТОР ССЫЛОК ---
def get_trade_url(exchange, symbol):
    try:
        if '->' in exchange: 
            return f"https://www.google.com/search?q={symbol}+crypto+arbitrage"
            
        base, quote = symbol.split('/')
        base = base.upper(); quote = quote.upper(); ex = exchange.lower()
        
        if ex == 'binance': return f"https://www.binance.com/en/trade/{base}_{quote}?type=spot"
        elif ex == 'bybit': return f"https://www.bybit.com/trade/spot/{base}/{quote}"
        elif ex == 'okx': return f"https://www.okx.com/trade-spot/{base.lower()}-{quote.lower()}"
        elif ex == 'gateio': return f"https://www.gate.io/trade/{base}_{quote}"
        elif ex == 'kucoin': return f"https://www.kucoin.com/trade/{base}-{quote}"
        elif ex == 'mexc': return f"https://www.mexc.com/exchange/{base}_{quote}"
        elif ex == 'htx' or ex == 'huobi': return f"https://www.htx.com/trade/{base.lower()}_{quote.lower()}"
        elif ex == 'bitget': return f"https://www.bitget.com/spot/{base}{quote}_SPBL"
        elif ex == 'kraken': return f"https://pro.kraken.com/app/trade/{base}-{quote}"
        elif ex == 'coinbase': return f"https://www.coinbase.com/advanced-trade/{base}-{quote}"
        elif ex == 'bingx': return f"https://bingx.com/en-us/spot/{base}USDT/"
        elif ex == 'poloniex': return f"https://poloniex.com/spot/{base}_{quote}"
        else: return f"https://www.google.com/search?q={ex}+{base}+{quote}+spot"
    except: return "https://google.com"

def create_ui():
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Roboto+Mono:wght@500;700&display=swap');
        body { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
        .market-header { font-size: 24px; font-weight: 800; color: #111827; margin-bottom: 15px; }
        .grid-layout { display: grid; grid-template-columns: 40px 1.5fr 1fr 1fr 1fr 1fr 2fr; align-items: center; }
        .table-header { color: #9ca3af; font-size: 12px; font-weight: 600; text-transform: uppercase; padding: 12px 10px; border-bottom: 1px solid #f3f4f6; }
        .table-row { background: white; padding: 16px 10px; border-bottom: 1px solid #f3f4f6; transition: all 0.2s ease; cursor: pointer; }
        .table-row:hover { background: #f9fafb; transform: translateY(-1px); box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
        .coin-name { font-weight: 800; color: #111827; font-size: 14px; }
        .stat-green { color: #10b981; font-weight: 700; font-size: 14px; font-family: 'Roboto Mono', monospace; }
        .stat-neutral { color: #6b7280; font-weight: 700; font-size: 14px; font-family: 'Roboto Mono', monospace; } 
        .stat-price { color: #6b7280; font-weight: 500; font-size: 13px; font-family: 'Roboto Mono', monospace; }
        .route-text { font-weight: 700; color: #374151; font-size: 12px; text-transform: uppercase; }
        .calc-box { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .locked-badge { background: #1f2937; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .blur-row { filter: blur(4px); pointer-events: none; opacity: 0.6; }
        a.route-link { text-decoration: none !important; border-bottom: none !important; color: #374151; }
    </style>
    ''')

    def instant_update():
        current_invest = app_state["investment"] or 0
        for item in app_state["data"]:
            item['profit'] = (item['spread'] / 100.0) * current_invest
        try:
            render_table_rows.refresh()
            if app_state.get("selected_symbol"): update_calc()
        except: pass

    def get_current_user_plan():
        username = app.storage.user.get('username')
        if not username: return "FREE"
        try:
            db = next(get_db())
            user_obj = get_user_by_username(db, username)
            return get_user_plan(db, user_obj.id) if user_obj else "FREE"
        except: return "FREE"
        finally: 
            if 'db' in locals(): db.close()

    # --- TOP MENU ---
    with ui.element('div').classes('fixed top-4 right-6 z-50'):
        user = app.storage.user.get('username', None)
        if user:
            with ui.button(user, icon='account_circle').props('flat color=grey-9 no-caps'):
                with ui.menu().classes('w-56'):
                    if app.storage.user.get('role') == 'admin':
                        ui.menu_item('АДМИН ПАНЕЛЬ', on_click=lambda: ui.navigate.to('/admin')).classes('text-blue-600 font-bold')
                        ui.separator()
                    ui.menu_item('Тарифы и Оплата', on_click=lambda: ui.navigate.to('/tariffs')).classes('text-purple-700 font-bold')
                    ui.separator()
                    ui.menu_item('Мой профиль', on_click=lambda: ui.navigate.to('/profile'))
                    ui.separator()
                    ui.menu_item('Выйти', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))).classes('text-red-600 font-bold')
        else:
            ui.button('ВОЙТИ', on_click=lambda: ui.navigate.to('/login')).props('unelevated color=black text-color=white size=sm round font-bold')

    # --- SIDEBAR ---
    with ui.left_drawer(value=True).classes('bg-white p-6 border-r border-gray-100'):
        ui.label("SPREADFLOW").classes('sidebar-title mb-1')
        ui.label("AI ARBITRAGE").classes('text-xs font-bold text-green-600 tracking-widest mb-8')
        
        # Инвестиция
        with ui.row().classes('w-full items-center justify-between mb-1'):
            ui.label("Инвестиция ($)").classes('text-xs font-bold text-gray-500 uppercase')
            ui.number(format='%.0f').bind_value(app_state, 'investment').on_value_change(instant_update).classes('w-20').props('dense borderless input-class="text-right font-bold"')
        ui.slider(min=100, max=10000, step=100).bind_value(app_state, 'investment').on_value_change(instant_update).classes('w-full mb-6').props('color=black')

        # Мин. Спред
        with ui.row().classes('w-full items-center justify-between mb-1'):
            ui.label("Мин. спред (%)").classes('text-xs font-bold text-gray-500 uppercase')
            ui.number(format='%.2f', step=0.1).bind_value(app_state, 'target_spread').on_value_change(instant_update).classes('w-20').props('dense borderless input-class="text-right font-bold"')
        ui.slider(min=-5.0, max=10.0, step=0.1).bind_value(app_state, 'target_spread').on_value_change(instant_update).classes('w-full mb-6').props('color=black')
        
        # Объем
        with ui.row().classes('w-full items-center justify-between mb-1'):
            ui.label("Мин. Объем ($)").classes('text-xs font-bold text-gray-500 uppercase')
            ui.number(format='%.0f', step=10000).bind_value(app_state, 'min_volume').on_value_change(instant_update).classes('w-24').props('dense borderless input-class="text-right font-bold"')
        ui.slider(min=0, max=5000000, step=10000).bind_value(app_state, 'min_volume').on_value_change(instant_update).classes('w-full mb-6').props('color=black')
        
        # --- СКРЫТАЯ ГАЛОЧКА (ТОЛЬКО ДЛЯ АДМИНА) ---
        if app.storage.user.get('role') == 'admin':
            ui.checkbox('Включить сложные (Chain)').bind_value(app_state, 'include_chains').on_value_change(instant_update).classes('text-sm font-bold text-red-700 mb-4')
        # -------------------------------------------
        
        ui.separator().classes('mb-4')

        # ФИЛЬТР БИРЖ
        with ui.expansion('Фильтр бирж', icon='account_balance').classes('w-full custom-expansion mb-2'):
            with ui.column().classes('pl-2 gap-1'):
                def toggle_ex(name, value):
                    if value and name not in app_state["selected_exchanges"]: app_state["selected_exchanges"].append(name)
                    elif not value and name in app_state["selected_exchanges"]: app_state["selected_exchanges"].remove(name)
                    save_config(app_state["selected_exchanges"], app_state["selected_coins"])
                    instant_update()
                for ex in DEFAULT_EXCHANGES:
                    ui.checkbox(ex.upper(), value=(ex in app_state["selected_exchanges"]), on_change=lambda e, x=ex: toggle_ex(x, e.value)).props('dense size=xs color=black')

        # ФИЛЬТР МОНЕТ
        with ui.expansion('Монеты (Топ-50)', icon='currency_bitcoin').classes('w-full custom-expansion'):
             with ui.column().classes('pl-2 gap-1 scroll-y h-64'): 
                display_coins = sorted([c for c in app_state["selected_coins"] if '/USDT' in c])[:50]
                ui.label(f"Всего сканируется: {len(app_state['selected_coins'])}").classes('text-xs text-gray-400')
                for coin in display_coins:
                    ui.label(coin).classes('text-xs font-medium text-gray-600')

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
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label("Рынок Live").classes('market-header')
            ui.label().bind_text_from(app_state, 'status_message').classes('text-xs font-bold bg-green-100 text-green-800 px-2 py-1 rounded')

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
                    ui.spinner('dots', size='3em', color='black')
                    ui.label('Ищем связки...').classes('text-gray-400 mt-4 font-medium animate-pulse')
                return

            current_plan = get_current_user_plan()
            limits = get_user_limits(current_plan)

            data = sorted(app_state["data"], key=lambda x: x['spread'], reverse=True)
            
            with ui.column().classes('w-full gap-0'):
                for item in data:
                    is_chain_route = 'via' in item['symbol']
                    
                    # --- ЕСЛИ ГАЛОЧКА ВЫКЛЮЧЕНА, backend их даже не ищет, но фильтр оставим для надежности ---
                    if is_chain_route and not app_state['include_chains']:
                        continue

                    if not is_chain_route and item['buy_ex'] not in app_state['selected_exchanges']: 
                        continue

                    if item['symbol'] not in limits['coins'] and not is_chain_route: continue 

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
                        target = app_state['target_spread'] or -10.0 
                        if item['spread'] < target: continue

                        is_profitable = item['spread'] > 0
                        stat_class = 'stat-green' if is_profitable else 'stat-neutral'
                        
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
                                    if '->' in b_ex:
                                         ui.label(b_ex).classes('route-text text-xs')
                                         ui.label(s_ex).classes('route-text text-xs')
                                    else:
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
                calc_container.set_visibility(False); return
            calc_container.set_visibility(True)
            item = next((x for x in app_state["data"] if x["symbol"] == sym), None)
            if item:
                lbl_pair_name.set_text(sym)
                price_text = f"Buy: {item['buy_price']} | Sell: {item['sell_price']}"
                lbl_pair_prices.set_text(price_text)
                total = item['profit'] * (app_state['loops'] or 1.0)
                lbl_total_profit.set_text(f"${total:.2f}")
            else: calc_container.set_visibility(False)

        def ui_tick():
            now = time.time()
            if app_state["last_update_ts"] > app_state.get('ui_updated_ts', 0):
                plan = get_current_user_plan()
                limits = get_user_limits(plan)
                if (now - app_state.get('ui_updated_ts', 0)) >= limits.get('refresh_rate', 1):
                    render_table_rows.refresh()
                    app_state["ui_updated_ts"] = now
                    if app_state.get("selected_symbol"): update_calc()
        ui.timer(0.5, ui_tick)