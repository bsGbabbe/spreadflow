import ccxt # Используем СТАНДАРТНЫЙ ccxt (как в старом коде)
import time
import asyncio
import urllib3
import concurrent.futures
from nicegui import run
from logger import log
from state import app_state
from config import DEFAULT_EXCHANGES

# Отключаем SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

exchanges_map = {}
TASK_STARTED = False 

# === НАСТРОЙКИ СКОРОСТИ (КАК В СТАРОМ КОДЕ) ===
MAX_THREADS = 20  # Точно как ползунок "Потоков" в Streamlit
# ==============================================

def init_exchanges_sync():
    """Синхронная инициализация (точь-в-точь как раньше)"""
    log.info("Connecting to exchanges (Standard Mode)...")
    
    # Заголовки как в браузере
    fake_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for eid in DEFAULT_EXCHANGES:
        if eid not in exchanges_map:
            try:
                exchange_class = getattr(ccxt, eid)
                exchange = exchange_class({
                    'enableRateLimit': True, 
                    'timeout': 5000, 
                    'verify': False,   # Отключаем проверку SSL
                    'headers': fake_headers
                })
                # Проверка не нужна, просто создаем объект
                exchanges_map[eid] = exchange
            except Exception as e:
                log.warning(f"Failed to init {eid}: {e}")
    return True

def get_price_worker(args):
    """Рабочая лошадка потока"""
    exchange, symbol = args
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        if price and price > 0:
            return {'ex': exchange.id, 'price': float(price), 'sym': symbol}
    except Exception:
        # Игнорируем ошибки (как в старом коде), просто идем дальше
        return None
    return None

def scan_market_sync(selected_exs, selected_cns):
    """
    Полная копия логики scan_market из старого кода.
    Использует ThreadPoolExecutor.
    """
    active_exs = [exchanges_map[e] for e in selected_exs if e in exchanges_map]
    if not active_exs: return []

    tasks_args = []
    # Формируем список задач (каждая задача - пара биржа+монета)
    for sym in selected_cns:
        for ex in active_exs:
            tasks_args.append((ex, sym))
    
    results = []
    
    # ЗАПУСКАЕМ 20 ПОТОКОВ (как было у вас)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Запускаем задачи
        future_to_url = {executor.submit(get_price_worker, arg): arg for arg in tasks_args}
        
        # Собираем результаты
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                pass
                
    return results

def calculate_logic(raw_data):
    """Математика"""
    grouped = {}
    for item in raw_data:
        sym = item['sym']
        if sym not in grouped: grouped[sym] = []
        grouped[sym].append(item)
    
    final_list = []
    invest = app_state["investment"]

    for sym, prices in grouped.items():
        if len(prices) > 1:
            min_p = min(prices, key=lambda x: x['price'])
            max_p = max(prices, key=lambda x: x['price'])
            
            p_buy = float(min_p['price'])
            p_sell = float(max_p['price'])
            
            if p_buy == 0: continue
            spread = ((p_sell - p_buy) / p_buy) * 100
            profit = (spread / 100.0) * invest
            
            final_list.append({
                "symbol": sym, 
                "spread": spread, 
                "profit": profit,
                "buy_price": p_buy, "sell_price": p_sell,
                "buy_ex": min_p['ex'], "sell_ex": max_p['ex']
            })
    
    final_list.sort(key=lambda x: x['spread'], reverse=True)
    app_state["data"] = final_list

async def background_task():
    global TASK_STARTED
    if TASK_STARTED: return
    TASK_STARTED = True

    app_state["status_message"] = "Подключение..."
    
    # 1. Запускаем инициализацию (в отдельном потоке, чтобы не морозить UI)
    await run.io_bound(init_exchanges_sync)
    
    app_state["exchanges_ready"] = True
    app_state["status_message"] = "Готово"
    log.info("System Ready (Thread Mode). Waiting for start...")
    
    try:
        while True:
            if app_state["is_running"]:
                current_exs = app_state["selected_exchanges"]
                current_cns = app_state["selected_coins"]
                
                if current_exs and current_cns:
                    start_t = time.time()
                    
                    # 2. ГЛАВНОЕ: Запускаем сканирование через ThreadPool
                    # run.io_bound позволяет синхронному коду работать внутри NiceGUI
                    raw_data = await run.io_bound(scan_market_sync, current_exs, current_cns)
                    
                    if raw_data:
                        calculate_logic(raw_data)
                        app_state["last_update_ts"] = time.time()
                        elapsed = time.time() - start_t
                        log.info(f"Cycle: {elapsed:.2f}s | Pairs: {len(app_state['data'])}")
                    else:
                        log.warning("No data found (Check VPN if persistent)")

            await asyncio.sleep(app_state["refresh_rate"])
            
    except asyncio.CancelledError:
        log.info("Stopping...")
    except Exception as e:
        log.error(f"Critical Backend Error: {e}")