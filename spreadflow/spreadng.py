from nicegui import ui, app, run
import ccxt
import json
import os
import urllib3
import asyncio
import time

# Отключаем SSL предупреждения
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
#          1. КОНФИГУРАЦИЯ И STATE
# ==========================================
CONFIG_FILE = "filter_config.json"
EXCHANGES_LIST = ['binance', 'bybit', 'okx', 'gateio', 'kucoin', 'huobi', 'mexc', 'htx']
COINS_LIST = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'LTC/USDT', 'ADA/USDT', 
    'DOGE/USDT', 'BNB/USDT', 'USDC/USDT', 'FDUSD/USDT', 'DAI/USDT', 'DOT/USDT',
    'AVAX/USDT', 'LINK/USDT', 'MATIC/USDT', 'TON/USDT'
]

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                # Возвращаем списки или дефолтные, если файл пустой
                return data.get("exchanges", EXCHANGES_LIST.copy()), data.get("coins", COINS_LIST.copy())
        except: pass
    return EXCHANGES_LIST.copy(), COINS_LIST.copy()

def save_config():
    # Сохраняем текущее состояние фильтров
    with open(CONFIG_FILE, 'w') as f:
        json.dump({
            "exchanges": state["selected_exchanges"],
            "coins": state["selected_coins"]
        }, f)

# Загружаем настройки при старте
saved_exs, saved_cns = load_config()

# Глобальное состояние
state = {
    "is_running": False,
    "data": [],
    "last_update_ts": 0,
    "ui_updated_ts": 0,
    "selected_symbol": None,
    "loops": 1.0,
    "history": {},
    "investment": 1000.0,
    "target_spread": 0.1,
    "refresh_rate": 3.0,
    "exchanges_ready": False,
    "status_message": "Запуск...",
    # ФИЛЬТРЫ
    "selected_exchanges": saved_exs,
    "selected_coins": saved_cns
}

def safe_float(val, default=0.0):
    try: return float(val)
    except: return default

exchanges_map = {}

# ==========================================
#          2. БЭКЕНД (СКАНИРОВАНИЕ)
# ==========================================
def init_exchanges_sync():
    """Инициализация бирж"""
    print("Connecting to exchanges...")
    for eid in EXCHANGES_LIST:
        if eid not in exchanges_map:
            try:
                cls = getattr(ccxt, eid)
                exchanges_map[eid] = cls({'enableRateLimit': True, 'timeout': 10000, 'verify': False})
            except: pass
    return True

def fetch_prices_sync(target_exchanges, target_coins):
    """Сбор цен только по выбранным биржам и монетам"""
    results = []
    # Фильтруем объекты бирж
    active_exs = [exchanges_map[e] for e in target_exchanges if e in exchanges_map]
    
    for ex in active_exs:
        for sym in target_coins:
            try:
                ticker = ex.fetch_ticker(sym)
                price = ticker['last']
                if price and price > 0:
                    results.append({'ex': ex.id, 'price': float(price), 'sym': sym})
            except: pass
    return results

async def background_task():
    """Главный цикл"""
    state["status_message"] = "Подключение..."
    await run.io_bound(init_exchanges_sync)
    state["exchanges_ready"] = True
    state["status_message"] = "Готово"
    
    while True:
        try:
            if state["is_running"]:
                # Берем ТЕКУЩИЕ фильтры из state
                current_exs = state["selected_exchanges"]
                current_cns = state["selected_coins"]
                
                if not current_exs or not current_cns:
                    print("Filters empty, skipping scan...")
                else:
                    # Сканируем
                    raw_data = await run.io_bound(fetch_prices_sync, current_exs, current_cns)
                    if raw_data:
                        calculate_logic(raw_data)
                        state["last_update_ts"] = time.time()
                
            await asyncio.sleep(state["refresh_rate"])
            
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

def calculate_logic(raw_data):
    # Группировка
    grouped = {}
    for item in raw_data:
        sym = item['sym']
        if sym not in grouped: grouped[sym] = []
        grouped[sym].append(item)
    
    final_list = []
    invest = safe_float(state["investment"], 0.0)

    for sym, prices in grouped.items():
        if len(prices) > 1:
            min_p = min(prices, key=lambda x: x['price'])
            max_p = max(prices, key=lambda x: x['price'])
            p_buy = safe_float(min_p['price'])
            p_sell = safe_float(max_p['price'])
            
            if p_buy == 0: continue
            spread = ((p_sell - p_buy) / p_buy) * 100
            profit = (spread / 100.0) * invest
            
            final_list.append({
                "symbol": sym, "spread": spread, "profit": profit,
                "buy_price": p_buy, "sell_price": p_sell,
                "buy_ex": min_p['ex'], "sell_ex": max_p['ex']
            })
    
    final_list.sort(key=lambda x: x['spread'], reverse=True)
    state["data"] = final_list

# ==========================================
#          3. ИНТЕРФЕЙС
# ==========================================
@ui.page('/')
def main_page():
    # CSS
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@500;700&display=swap');
        body { background-color: #f3f4f6; }
        .calc-box { background: white; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .grid-row { display: grid; grid-template-columns: 50px 1.5fr 1fr 1fr 1fr 1fr 2fr; background: white; padding: 8px 10px; align-items: center; border-bottom: 1px solid #eee; font-family: 'Roboto Mono', monospace; font-size: 13px; }
        .grid-header { display: grid; grid-template-columns: 50px 1.5fr 1fr 1fr 1fr 1fr 2fr; background: #e5e7eb; padding: 10px; font-weight: bold; font-family: 'Roboto Mono', monospace; font-size: 13px; border-radius: 5px; }
        .trend-up { color: #16a34a; } .trend-down { color: #dc2626; }
    </style>
    ''')

    # --- ЛЕВОЕ МЕНЮ (САЙДБАР) ---
    with ui.left_drawer(value=True).classes('bg-white p-4 shadow-lg'):
        ui.label("SPREADFLOW AI").classes('text-xl font-bold text-green-700 mb-4')
        
        status_label = ui.label('Инициализация...').classes('text-xs font-bold text-orange-500 mb-2')
        
        # Кнопка СТАРТ/СТОП
        btn_start = ui.button('ЗАГРУЗКА...').classes('w-full mb-4 font-bold')
        def toggle_start():
            if not state["selected_exchanges"] or not state["selected_coins"]:
                ui.notify('Выберите хотя бы одну биржу и монету!', type='warning')
                return
            state["is_running"] = not state["is_running"]
            update_start_btn()
        btn_start.on_click(toggle_start)
        btn_start.disable()

        def update_start_btn():
            if not state["exchanges_ready"]: return
            btn_start.enable()
            if state["is_running"]:
                btn_start.props('color=red icon=stop label="ОСТАНОВИТЬ"')
            else:
                btn_start.props('color=green icon=rocket label="ЗАПУСТИТЬ"')

        # --- НАСТРОЙКИ ---
        ui.label("Инвестиция ($)").classes('text-xs font-bold text-gray-500')
        ui.number().bind_value(state, 'investment').classes('w-full mb-2') 

        ui.label("Целевой спред (%)").classes('text-xs font-bold text-gray-500')
        ui.slider(min=0.0, max=5.0, step=0.1).bind_value(state, 'target_spread').classes('w-full mb-2')
        
        ui.label("Обновление (сек)").classes('text-xs font-bold text-gray-500')
        ui.slider(min=1, max=10, step=1).bind_value(state, 'refresh_rate').classes('w-full mb-4')
        
        ui.separator()
        
        # --- ФИЛЬТРЫ (ВЫПАДАЮЩИЕ СПИСКИ) ---
        
        # 1. Биржи
        with ui.expansion('🏦 Фильтр бирж', icon='account_balance').classes('w-full border rounded mb-2'):
            with ui.column().classes('p-2'):
                def toggle_exchange(name, value):
                    if value: 
                        if name not in state["selected_exchanges"]: state["selected_exchanges"].append(name)
                    else:
                        if name in state["selected_exchanges"]: state["selected_exchanges"].remove(name)
                    save_config() # Сохраняем сразу

                for ex in EXCHANGES_LIST:
                    is_checked = ex in state["selected_exchanges"]
                    # Создаем чекбокс и привязываем логику
                    ui.checkbox(ex, value=is_checked, on_change=lambda e, x=ex: toggle_exchange(x, e.value))

        # 2. Монеты
        with ui.expansion('🪙 Фильтр монет', icon='currency_bitcoin').classes('w-full border rounded mb-4'):
             with ui.column().classes('p-2'):
                def toggle_coin(name, value):
                    if value:
                        if name not in state["selected_coins"]: state["selected_coins"].append(name)
                    else:
                        if name in state["selected_coins"]: state["selected_coins"].remove(name)
                    save_config()

                for coin in COINS_LIST:
                    is_checked = coin in state["selected_coins"]
                    ui.checkbox(coin, value=is_checked, on_change=lambda e, x=coin: toggle_coin(x, e.value))


    # --- ЦЕНТРАЛЬНАЯ ЧАСТЬ ---
    with ui.column().classes('w-full p-4 gap-4'):
        
        # === КАЛЬКУЛЯТОР ===
        with ui.row().classes('calc-box w-full items-center justify-between') as calc_container:
            calc_container.set_visibility(False)
            
            with ui.column().classes('gap-0'):
                lbl_pair_name = ui.label("PAIR").classes('text-2xl font-bold text-green-700')
                lbl_pair_prices = ui.label("...").classes('text-sm text-gray-500')
            
            with ui.row().classes('items-center gap-4'):
                ui.label("Оборотов:").classes('font-bold')
                inp_loops = ui.number(min=1, value=1.0, step=1.0).classes('w-24 text-lg')
                inp_loops.bind_value(state, 'loops')
            
            with ui.column().classes('items-end'):
                ui.label("ИТОГ").classes('text-xs font-bold text-gray-400')
                lbl_total_profit = ui.label("$0.00").classes('text-3xl font-bold text-green-600')

        # === ТАБЛИЦА ===
        ui.label("РЫНОК ONLINE").classes('text-xl font-bold text-gray-700')
        
        with ui.row().classes('grid-header w-full'):
            for h in ["", "МОНЕТА", "СПРЕД", "ПРОФИТ", "КУПИТЬ", "ПРОДАТЬ", "МАРШРУТ"]:
                ui.label(h)
        
        @ui.refreshable
        def render_table_rows():
            if not state["data"]:
                if state["is_running"]:
                    ui.label("Сканирование...").classes('w-full text-center text-gray-400 py-4')
                else:
                    ui.label("Нажмите ЗАПУСТИТЬ").classes('w-full text-center text-gray-400 py-4')
                return

            # Фильтрация и сортировка
            display_data = sorted(state["data"], key=lambda x: x['spread'], reverse=True)
            
            for item in display_data:
                sym = item['symbol']
                prev = state["history"].get(sym, item['spread'])
                arr, color_cls = ("⬆", "trend-up") if item['spread'] > prev else \
                                 ("⬇", "trend-down") if item['spread'] < prev else \
                                 ("➖", "text-gray-400")
                state["history"][sym] = item['spread']

                with ui.row().classes('grid-row w-full'):
                    def select_pair(s=sym):
                        state["selected_symbol"] = s
                        update_calculator_data()
                    
                    ui.button('🧮', on_click=select_pair).props('flat dense round color=green')
                    
                    with ui.row().classes('items-center gap-2'):
                        ui.html(f"<span class='{color_cls} text-lg'>{arr}</span>")
                        ui.label(sym).classes('font-bold')
                    
                    spd_cls = 'text-green-600 font-bold' if item['spread'] >= state['target_spread'] else 'text-red-600 font-bold'
                    ui.label(f"{item['spread']:.2f}%").classes(spd_cls)
                    ui.label(f"${item['profit']:.2f}")
                    ui.label(f"{item['buy_price']}")
                    ui.label(f"{item['sell_price']}")
                    ui.label(f"{item['buy_ex']} → {item['sell_ex']}").classes('bg-gray-100 px-2 rounded text-xs font-bold')

        render_table_rows()

    # === ЛОГИКА UI ===
    def update_calculator_data():
        sym = state["selected_symbol"]
        if not sym:
            calc_container.set_visibility(False)
            return
        
        calc_container.set_visibility(True)
        current_data = next((x for x in state["data"] if x["symbol"] == sym), None)
        
        if current_data:
            lbl_pair_name.set_text(sym)
            lbl_pair_prices.set_text(f"Buy: {current_data['buy_price']} | Sell: {current_data['sell_price']}")
            total = current_data['profit'] * state['loops']
            lbl_total_profit.set_text(f"${total:.2f}")
        else:
            lbl_pair_prices.set_text("Ожидание данных...")

    def fast_ui_tick():
        # Статус бирж
        if state["exchanges_ready"] and status_label.text == 'Инициализация...':
            status_label.set_text("ГОТОВО")
            status_label.classes(replace='text-green-500')
            update_start_btn()

        # Рефреш таблицы только при новых данных
        if state["last_update_ts"] > state["ui_updated_ts"]:
            render_table_rows.refresh()
            state["ui_updated_ts"] = time.time()
            
        # Калькулятор
        if state["selected_symbol"]:
            update_calculator_data()

    ui.timer(0.1, fast_ui_tick)

app.on_startup(lambda: asyncio.create_task(background_task()))
ui.run(title="SpreadFlow AI", port=8080, reload=False, show=True)