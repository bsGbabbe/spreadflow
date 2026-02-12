import ccxt
import time
import asyncio
import urllib3
from nicegui import run
from logger import log
from config import DEFAULT_EXCHANGES

# Отключаем SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

exchanges_map = {}
TASK_STARTED = False 

# Глобальные переменные
GLOBAL_OPPORTUNITIES = []
GLOBAL_LAST_UPDATE = 0
DISCOVERED_COINS = set()

def init_exchanges_sync():
    """Инициализация бирж"""
    log.info("Connecting to exchanges (Auto-Discovery Mode)...")
    fake_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for eid in DEFAULT_EXCHANGES:
        if eid not in exchanges_map:
            try:
                exchange_class = getattr(ccxt, eid)
                exchanges_map[eid] = exchange_class({
                    'enableRateLimit': True, 
                    'timeout': 10000, 
                    'verify': False, 
                    'headers': fake_headers
                })
            except Exception as e:
                log.warning(f"Failed to init {eid}: {e}")
    return True

def fetch_all_tickers_sync(exchange_id):
    """
    Запрашивает ВСЕ тикеры с биржи и фильтрует только USDT пары.
    """
    ex = exchanges_map.get(exchange_id)
    if not ex: return exchange_id, {}
    
    try:
        tickers = ex.fetch_tickers()
        clean_data = {}
        for symbol, data in tickers.items():
            if symbol.endswith('/USDT'):
                if data and data['last'] and data['last'] > 0:
                    clean_data[symbol] = float(data['last'])
        return exchange_id, clean_data
    except Exception as e:
        return exchange_id, {}

def calculate_global_spreads(prices_cache):
    global GLOBAL_OPPORTUNITIES, GLOBAL_LAST_UPDATE, DISCOVERED_COINS
    
    temp_list = []
    found_coins_set = set() 
    
    for sym, ex_prices in prices_cache.items():
        found_coins_set.add(sym)
        
        if len(ex_prices) < 2: continue 

        sorted_prices = sorted(ex_prices.items(), key=lambda x: x[1])
        min_ex, min_p = sorted_prices[0]
        max_ex, max_p = sorted_prices[-1]
        
        if min_p <= 0: continue

        spread = ((max_p - min_p) / min_p) * 100
        
        # === ИЗМЕНЕНИЕ: Убран лимит 200%. Теперь хоть 10000% ===
        if spread < 0.1: continue

        temp_list.append({
            "symbol": sym, 
            "spread": spread,
            "buy_price": min_p, "sell_price": max_p,
            "buy_ex": min_ex, "sell_ex": max_ex
        })
    
    temp_list.sort(key=lambda x: x['spread'], reverse=True)
    
    GLOBAL_OPPORTUNITIES = temp_list
    GLOBAL_LAST_UPDATE = time.time()
    
    if len(DISCOVERED_COINS) == 0 or len(found_coins_set) > len(DISCOVERED_COINS):
        DISCOVERED_COINS = found_coins_set
        log.info(f"🔎 Discovered {len(DISCOVERED_COINS)} unique USDT pairs")

    if len(temp_list) > 0:
        top = temp_list[0]
        log.info(f"⚡ Scan: {len(temp_list)} spreads. Best: {top['symbol']} {top['spread']:.2f}%")

async def background_task():
    global TASK_STARTED
    if TASK_STARTED: return
    TASK_STARTED = True

    await run.io_bound(init_exchanges_sync)
    log.info("🚀 Full-Market Engine Started")
    
    local_prices = {} 

    while True:
        try:
            tasks = []
            for eid in DEFAULT_EXCHANGES:
                if eid in exchanges_map:
                    tasks.append(run.io_bound(fetch_all_tickers_sync, eid))
            
            for future in asyncio.as_completed(tasks):
                ex_id, new_prices = await future
                if new_prices:
                    for sym, price in new_prices.items():
                        if sym not in local_prices: local_prices[sym] = {}
                        local_prices[sym][ex_id] = price
                    
                    calculate_global_spreads(local_prices)
            
            await asyncio.sleep(3) 
        except Exception as e:
            log.error(f"Core Loop Error: {e}")
            await asyncio.sleep(5)