import ccxt 
import time
import asyncio
import urllib3
import concurrent.futures
from nicegui import run
from logger import log
from state import app_state
from config import DEFAULT_EXCHANGES, DEFAULT_COINS

# Отключаем SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

exchanges_map = {}
TASK_STARTED = False 

# === ЗАЩИТА СЕРВЕРА (ЛИМИТЫ) ===
MAX_THREADS = 10        
TOP_COINS_LIMIT = 150   
MARKET_LEADER = 'binance' 
# ===============================

def init_exchanges_sync():
    """Синхронная инициализация бирж"""
    log.info("Connecting to exchanges...")
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
                    'verify': False,   
                    'headers': fake_headers
                })
                exchanges_map[eid] = exchange
            except Exception as e:
                log.warning(f"Failed to init {eid}: {e}")
    return True

def fetch_top_liquid_coins():
    """АВТО-СКАНЕР: Загружает ТОП монет по объему"""
    log.info(f"Auto-fetching TOP-{TOP_COINS_LIMIT} coins by volume from {MARKET_LEADER}...")
    try:
        leader = getattr(ccxt, MARKET_LEADER)({'timeout': 10000, 'enableRateLimit': True})
        markets = leader.fetch_tickers()
        
        sorted_tickers = []
        for symbol, ticker in markets.items():
            if '/USDT' in symbol and ticker['quoteVolume'] is not None:
                sorted_tickers.append({
                    'symbol': symbol,
                    'vol': ticker['quoteVolume']
                })
        
        sorted_tickers.sort(key=lambda x: x['vol'], reverse=True)
        top_usdt_pairs = [x['symbol'] for x in sorted_tickers[:TOP_COINS_LIMIT]]
        clean_pairs = [p for p in top_usdt_pairs if 'UP/' not in p and 'DOWN/' not in p]
        
        log.info(f"Successfully loaded {len(clean_pairs)} top pairs (Vol Leader: {clean_pairs[0]})")
        return clean_pairs
    except Exception as e:
        log.error(f"Failed to fetch top coins: {e}. Using fallback list.")
        return DEFAULT_COINS

def generate_routing_pairs(base_coins):
    """Генерирует кросс-пары (BTC, ETH, BNB)"""
    routing_pairs = []
    bridges = ['BTC', 'ETH', 'BNB']
    
    for pair in base_coins:
        try:
            base = pair.split('/')[0] 
            for bridge in bridges:
                if base == bridge: continue 
                routing_pairs.append(f"{base}/{bridge}")
        except:
            continue
    return list(set(base_coins + routing_pairs))

def get_price_worker(args):
    """Воркер для получения цены"""
    exchange, symbol = args
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        vol = ticker.get('quoteVolume') 
        if vol is None:
             vol = ticker.get('baseVolume', 0) * price

        if price and price > 0:
            return {'ex': exchange.id, 'price': float(price), 'vol': float(vol), 'sym': symbol}
    except Exception:
        return None
    return None

def scan_market_sync(selected_exs, selected_cns):
    active_exs = [exchanges_map[e] for e in selected_exs if e in exchanges_map]
    if not active_exs: return []

    tasks_args = []
    for sym in selected_cns:
        for ex in active_exs:
            tasks_args.append((ex, sym))
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_url = {executor.submit(get_price_worker, arg): arg for arg in tasks_args}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data: results.append(data)
            except Exception: pass
    return results

def calculate_chain_routes(raw_data, invest):
    """
    Поиск цепочек (Только если включено в настройках)
    """
    chains = []
    min_vol = app_state.get("min_volume", 0)
    prices_map = {}
    for item in raw_data:
        sym = item['sym']
        ex = item['ex']
        if sym not in prices_map: prices_map[sym] = {}
        prices_map[sym][ex] = item

    cross_pairs = [item for item in raw_data if '/USDT' not in item['sym']]
    
    for cross in cross_pairs:
        try:
            target_coin, bridge_coin = cross['sym'].split('/')
        except: continue
            
        bridge_usdt_sym = f"{bridge_coin}/USDT"
        target_usdt_sym = f"{target_coin}/USDT"
        
        if bridge_usdt_sym not in prices_map or target_usdt_sym not in prices_map: continue
            
        best_bridge_buy = min(prices_map[bridge_usdt_sym].values(), key=lambda x: x['price'])
        mid_step = cross 
        best_target_sell = max(prices_map[target_usdt_sym].values(), key=lambda x: x['price'])
        
        bottleneck_vol = min(best_bridge_buy['vol'], mid_step['vol'], best_target_sell['vol'])
        if bottleneck_vol < min_vol: continue
        
        amount_bridge = invest / best_bridge_buy['price']
        amount_target = amount_bridge / mid_step['price'] 
        final_usdt = amount_target * best_target_sell['price']
        
        profit = final_usdt - invest
        spread = (profit / invest) * 100
        
        if spread > -10.0: 
            chains.append({
                "symbol": f"{target_coin} (via {bridge_coin})", 
                "spread": spread,
                "profit": profit,
                "buy_price": f"{best_bridge_buy['price']:.2f}", 
                "sell_price": f"{best_target_sell['price']:.2f}",
                "buy_ex": f"{best_bridge_buy['ex'].upper()} -> {mid_step['ex'].upper()}",
                "sell_ex": f"{best_target_sell['ex'].upper()}",
                "vol": bottleneck_vol
            })
    return chains

def calculate_logic(raw_data):
    grouped = {}
    for item in raw_data:
        sym = item['sym']
        if sym not in grouped: grouped[sym] = []
        grouped[sym].append(item)
    
    final_list = []
    invest = app_state["investment"]
    min_vol = app_state.get("min_volume", 0) 

    # 1. Всегда считаем прямые связки
    for sym, prices in grouped.items():
        if '/USDT' not in sym: continue 
        if len(prices) > 1:
            min_p = min(prices, key=lambda x: x['price'])
            max_p = max(prices, key=lambda x: x['price'])
            
            if min_vol > 0:
                if min_p['vol'] < min_vol or max_p['vol'] < min_vol: continue

            p_buy = float(min_p['price'])
            p_sell = float(max_p['price'])
            if p_buy == 0: continue
            spread = ((p_sell - p_buy) / p_buy) * 100
            profit = (spread / 100.0) * invest
            
            final_list.append({
                "symbol": sym, "spread": spread, "profit": profit,
                "buy_price": p_buy, "sell_price": p_sell,
                "buy_ex": min_p['ex'], "sell_ex": max_p['ex']
            })
    
    # 2. ОПТИМИЗАЦИЯ: Считаем сложные цепочки ТОЛЬКО если включена галочка
    chain_results = []
    if app_state.get('include_chains', False):
        chain_results = calculate_chain_routes(raw_data, invest)
    
    full_result = final_list + chain_results
    full_result.sort(key=lambda x: x['spread'], reverse=True)
    app_state["data"] = full_result

async def background_task():
    global TASK_STARTED
    if TASK_STARTED: return
    TASK_STARTED = True

    app_state["status_message"] = "Подключение..."
    await run.io_bound(init_exchanges_sync)
    
    # --- ГИБРИДНАЯ ЗАГРУЗКА ---
    app_state["status_message"] = "Анализ рынка (Hybrid)..."
    log.info("Downloading TOP markets data...")
    
    # 1. Авто-Топ (Ликвидность)
    top_coins = await run.io_bound(fetch_top_liquid_coins)
    
    # 2. Ручной список (Волатильность/Мемы из config.py)
    # Объединяем списки, убирая дубликаты
    combined_coins = list(set(top_coins + DEFAULT_COINS))
    
    # 3. Генерируем пути
    full_list = generate_routing_pairs(combined_coins)
    
    app_state["selected_coins"] = full_list
    log.info(f"Total pairs to scan: {len(full_list)} (Top + Manual)")
    # --------------------------

    app_state["exchanges_ready"] = True
    app_state["status_message"] = "Готово"
    log.info("System Ready. Auto-mining enabled.")
    
    try:
        while True:
            current_exs = app_state["selected_exchanges"]
            current_cns = app_state["selected_coins"]
            
            if current_exs and current_cns:
                start_t = time.time()
                raw_data = await run.io_bound(scan_market_sync, current_exs, current_cns)
                
                if raw_data:
                    calculate_logic(raw_data)
                    app_state["last_update_ts"] = time.time()
                    elapsed = time.time() - start_t
                    mode = "SIMPLE+CHAIN" if app_state.get('include_chains') else "SIMPLE"
                    log.info(f"Cycle [{mode}]: {elapsed:.2f}s | Found: {len(app_state['data'])} ops")
                else:
                    log.warning("No data found")

            await asyncio.sleep(app_state["refresh_rate"])
            
    except asyncio.CancelledError:
        log.info("Stopping...")
    except Exception as e:
        log.error(f"Critical Backend Error: {e}")