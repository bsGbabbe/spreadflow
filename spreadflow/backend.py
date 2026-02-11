import ccxt
import time
import asyncio
import urllib3
from nicegui import run
from logger import log
from config import DEFAULT_EXCHANGES, DEFAULT_COINS

# Отключаем SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

exchanges_map = {}
TASK_STARTED = False 

# === ГЛОБАЛЬНЫЕ ДАННЫЕ (ОБЩИЕ ДЛЯ ВСЕХ) ===
# Сюда сканер складывает все найденные связки.
# Пользователи читают отсюда, применяя свои фильтры.
GLOBAL_OPPORTUNITIES = []
GLOBAL_LAST_UPDATE = 0

def init_exchanges_sync():
    """Инициализация бирж (подключение)"""
    log.info("Connecting to exchanges (Batch Mode)...")
    fake_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for eid in DEFAULT_EXCHANGES:
        if eid not in exchanges_map:
            try:
                exchange_class = getattr(ccxt, eid)
                exchanges_map[eid] = exchange_class({
                    'enableRateLimit': True, 
                    'timeout': 4000, 
                    'verify': False, 
                    'headers': fake_headers
                })
            except Exception as e:
                log.warning(f"Failed to init {eid}: {e}")
    return True

def fetch_tickers_batch_sync(exchange_id, symbols):
    """
    ОПТИМИЗАЦИЯ: Забирает цены СРАЗУ ПО ВСЕМ МОНЕТАМ одним запросом.
    Вместо 50 запросов делаем 1.
    """
    ex = exchanges_map.get(exchange_id)
    if not ex: return exchange_id, {}
    
    try:
        # ccxt fetch_tickers забирает всё сразу
        tickers = ex.fetch_tickers(symbols)
        
        clean_data = {}
        for sym, data in tickers.items():
            if data and data['last']:
                clean_data[sym] = float(data['last'])
        
        return exchange_id, clean_data
        
    except Exception as e:
        # log.debug(f"Batch fetch error {exchange_id}: {e}")
        return exchange_id, {}

def calculate_global_spreads(prices_cache):
    """Считает спреды по всем монетам и сохраняет в глобальную переменную"""
    global GLOBAL_OPPORTUNITIES, GLOBAL_LAST_UPDATE
    
    temp_list = []
    
    for sym, ex_prices in prices_cache.items():
        if len(ex_prices) < 2: continue # Нужно минимум 2 биржи

        sorted_prices = sorted(ex_prices.items(), key=lambda x: x[1])
        min_ex, min_p = sorted_prices[0]
        max_ex, max_p = sorted_prices[-1]
        
        if min_p <= 0: continue

        spread = ((max_p - min_p) / min_p) * 100
        
        # Отсекаем явные ошибки (>200%), остальное оставляем для фильтров юзера
        if spread > 200.0: continue 

        temp_list.append({
            "symbol": sym, 
            "spread": spread,
            "buy_price": min_p, "sell_price": max_p,
            "buy_ex": min_ex, "sell_ex": max_ex
        })
    
    # Сортируем: самые жирные спреды сверху
    temp_list.sort(key=lambda x: x['spread'], reverse=True)
    
    GLOBAL_OPPORTUNITIES = temp_list
    GLOBAL_LAST_UPDATE = time.time()

async def background_task():
    """Основной цикл сканера"""
    global TASK_STARTED
    if TASK_STARTED: return
    TASK_STARTED = True

    await run.io_bound(init_exchanges_sync)
    log.info("🚀 Optimized Engine Started")
    
    # Локальный кэш цен для цикла
    local_prices = {} 

    while True:
        try:
            tasks = []
            # Сканируем ВСЕ биржи параллельно
            for eid in DEFAULT_EXCHANGES:
                if eid in exchanges_map:
                    tasks.append(run.io_bound(fetch_tickers_batch_sync, eid, DEFAULT_COINS))
            
            # По мере поступления ответов обновляем цены
            for future in asyncio.as_completed(tasks):
                ex_id, new_prices = await future
                
                if new_prices:
                    for sym, price in new_prices.items():
                        if sym not in local_prices: local_prices[sym] = {}
                        local_prices[sym][ex_id] = price
                    
                    # Пересчитываем таблицу сразу, как пришли данные
                    calculate_global_spreads(local_prices)
            
            await asyncio.sleep(1) # Короткая пауза, чтобы не душить API
            
        except Exception as e:
            log.error(f"Core Loop Error: {e}")
            await asyncio.sleep(5)