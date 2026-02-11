import json
import os
from logger import log

CONFIG_FILE = "filter_config.json"

DEFAULT_EXCHANGES = ['binance', 'bybit', 'okx', 'gateio', 'kucoin', 'huobi', 'mexc', 'htx']

# "Золотая Сотня" - самые ликвидные и волатильные пары
DEFAULT_COINS = [
    # --- MAJORS ---
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT',
    'LINK/USDT', 'DOT/USDT', 'MATIC/USDT', 'LTC/USDT', 'BCH/USDT', 'UNI/USDT',
    
    # --- MEMES (Высокий спред!) ---
    'DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'BONK/USDT', 'WIF/USDT', 'FLOKI/USDT', 'MEME/USDT',
    
    # --- LAYER 1 / LAYER 2 ---
    'ARB/USDT', 'OP/USDT', 'SUI/USDT', 'SEI/USDT', 'APT/USDT', 'TIA/USDT', 'NEAR/USDT', 
    'ATOM/USDT', 'INJ/USDT', 'FTM/USDT', 'SUI/USDT', 'KAS/USDT',
    
    # --- AI & GAMING ---
    'RNDR/USDT', 'FET/USDT', 'AGIX/USDT', 'OCEAN/USDT', 'IMX/USDT', 'GALA/USDT', 'SAND/USDT',
    
    # --- STABLECOINS (Для проверки) ---
    'USDC/USDT', 'FDUSD/USDT',
    
    # --- HIGH VOLATILITY / NEW ---
    'ORDI/USDT', 'SATS/USDT', 'BLUR/USDT', 'JTO/USDT', 'PYTH/USDT', 'JUP/USDT',
    'STRK/USDT', 'DYM/USDT', 'ALT/USDT', 'MANTA/USDT', 'XAI/USDT'
]

def load_config():
    """Загрузка настроек из JSON"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                log.info("Config loaded successfully.")
                
                # Если в сохраненном файле старый список монет, объединяем его с новым DEFAULT
                saved_coins = data.get("coins", [])
                
                # Это гарантирует, что при обновлении кода новые монеты появятся в фильтре
                # если пользователь их еще не удалял специально
                if len(saved_coins) < 5: 
                    return data.get("exchanges", DEFAULT_EXCHANGES.copy()), DEFAULT_COINS.copy()
                    
                return data.get("exchanges", DEFAULT_EXCHANGES.copy()), saved_coins
        except Exception as e:
            log.error(f"Config load error: {e}")
    return DEFAULT_EXCHANGES.copy(), DEFAULT_COINS.copy()

def save_config(exchanges, coins):
    """Сохранение настроек в JSON"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"exchanges": exchanges, "coins": coins}, f)
        log.info("Config saved.")
    except Exception as e:
        log.error(f"Config save error: {e}")