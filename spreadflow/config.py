import json
import os
from logger import log

CONFIG_FILE = "filter_config.json"

# === СПИСОК БИРЖ ===
# Добавили: bitget, kraken, coinbase, bingx, poloniex
DEFAULT_EXCHANGES = [
    'binance', 'bybit', 'okx', 'gateio', 'kucoin', 
    'mexc', 'htx', 'bitget', 'kraken', 'coinbase', 
    'bingx', 'poloniex'
]

# === РЕЗЕРВНЫЙ СПИСОК ===
DEFAULT_COINS = [
    # --- TOP MAJORS ---
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT',
    'LINK/USDT', 'DOT/USDT', 'MATIC/USDT', 'LTC/USDT', 'BCH/USDT', 'UNI/USDT', 'TRX/USDT',
    'ETC/USDT', 'FIL/USDT', 'HBAR/USDT', 'XLM/USDT', 'VET/USDT', 'ICP/USDT', 'NEAR/USDT',
    'ATOM/USDT', 'APT/USDT', 'QNT/USDT', 'STX/USDT', 'GRT/USDT', 'RUNE/USDT',
    
    # --- TRENDING / NEW / HOT ---
    'TON/USDT', 'NOT/USDT', 'TAO/USDT', 'ENA/USDT', 'ETHFI/USDT', 'W/USDT', 'ZK/USDT',
    'ZRO/USDT', 'BLAST/USDT', 'IO/USDT', 'REZ/USDT', 'SAGA/USDT', 'TNSR/USDT',
    
    # --- MEMES ---
    'DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'BONK/USDT', 'WIF/USDT', 'FLOKI/USDT', 
    'BOME/USDT', 'MEME/USDT', 'PEOPLE/USDT', '1000SATS/USDT', 'ORDI/USDT', 'SLERF/USDT',
    'MEW/USDT', 'DEGEN/USDT', 'TURBO/USDT', 'MOG/USDT', 'BRETT/USDT',
    
    # --- AI & RWA ---
    'RNDR/USDT', 'FET/USDT', 'AGIX/USDT', 'OCEAN/USDT', 'ARKM/USDT', 'WLD/USDT',
    'ONDO/USDT', 'PENDLE/USDT', 'TRU/USDT', 'POLYX/USDT', 'GFI/USDT',
    
    # --- LAYER 1 / LAYER 2 / DEFI ---
    'ARB/USDT', 'OP/USDT', 'STRK/USDT', 'SUI/USDT', 'SEI/USDT', 'TIA/USDT', 'INJ/USDT',
    'FTM/USDT', 'KAS/USDT', 'MINA/USDT', 'DYM/USDT', 'ALT/USDT', 'MANTA/USDT', 'XAI/USDT',
    'PYTH/USDT', 'JUP/USDT', 'ZETA/USDT', 'RON/USDT', 'BLUR/USDT', 'JTO/USDT', 'CYBER/USDT',
    'AAVE/USDT', 'MKR/USDT', 'SNX/USDT', 'CRV/USDT', 'LDO/USDT', 'DYDX/USDT'
]

# === 2. АВТО-ГЕНЕРАЦИЯ КРОСС-ПАР ===
# Мы берем каждую монету из списка выше и добавляем к ней пары BTC, ETH и BNB.
# Это "дублирует" простые пары в кроссплатформенные, как ты просил.

ROUTING_COINS = []
BRIDGES = ['BTC', 'ETH', 'BNB'] # Монеты-мосты

for pair in DEFAULT_COINS:
    try:
        base_asset = pair.split('/')[0] # Берем "DOGE" из "DOGE/USDT"
        
        for bridge in BRIDGES:
            # Пропускаем бессмыслицу типа BTC/BTC или ETH/ETH
            if base_asset == bridge:
                continue
                
            # Создаем пару, например DOGE/BTC
            cross_pair = f"{base_asset}/{bridge}"
            ROUTING_COINS.append(cross_pair)
            
    except:
        continue

def load_config():
    """Загрузка настроек из JSON"""
    final_exchanges = DEFAULT_EXCHANGES.copy()
    final_coins = [] 

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                saved_coins = data.get("coins", [])
                
                # Если пользователь сам настроил биржи в UI, берем их,
                # но если там старый список - лучше обновить на новый DEFAULT
                saved_exs = data.get("exchanges", [])
                if len(saved_exs) < len(DEFAULT_EXCHANGES):
                    return DEFAULT_EXCHANGES.copy(), saved_coins if saved_coins else final_coins
                
                if saved_coins:
                    return saved_exs, saved_coins
                    
                return saved_exs, final_coins
        except Exception as e:
            log.error(f"Config load error: {e}")
    
    return final_exchanges, final_coins

def save_config(exchanges, coins):
    """Сохранение настроек в JSON"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"exchanges": exchanges, "coins": coins}, f)
        log.info("Config saved.")
    except Exception as e:
        log.error(f"Config save error: {e}")