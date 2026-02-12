import json
import os
from logger import log

CONFIG_FILE = "filter_config.json"

# === НАСТРОЙКИ ПОЧТЫ (SMTP) ===
# Для Gmail используйте App Password (Пароли приложений), а не обычный пароль!
SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 587,
    "user": "adm1nistrative.flow@gmail.com",      # <--- ВПИШИ СВОЮ ПОЧТУ
    "password": "seez wdxg jtbi pgos",     # <--- ВПИШИ ПАРОЛЬ ПРИЛОЖЕНИЯ
    "from_email": "noreply@spreadflow.ai"
}

# === СПИСОК БИРЖ ===
DEFAULT_EXCHANGES = [
    'binance', 'bybit', 'okx', 'gateio', 'kucoin', 
    'mexc', 'htx', 'bitget', 'kraken', 'coinbase', 
    'bingx', 'poloniex'
]

# === СПИСОК МОНЕТ ===
DEFAULT_COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT',
    'LINK/USDT', 'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'UNI/USDT', 'TRX/USDT',
    'ETC/USDT', 'FIL/USDT', 'HBAR/USDT', 'XLM/USDT', 'VET/USDT', 'ICP/USDT', 'NEAR/USDT',
    'ATOM/USDT', 'APT/USDT', 'QNT/USDT', 'STX/USDT', 'GRT/USDT', 'RUNE/USDT',
    'MATIC/USDT', 'POL/USDT', 
    'TON/USDT', 'NOT/USDT', 'TAO/USDT', 'ENA/USDT', 'ETHFI/USDT', 'W/USDT', 'ZK/USDT',
    'ZRO/USDT', 'BLAST/USDT', 'IO/USDT', 'REZ/USDT', 'SAGA/USDT', 'TNSR/USDT',
    'DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'BONK/USDT', 'WIF/USDT', 'FLOKI/USDT', 
    'BOME/USDT', 'MEME/USDT', 'PEOPLE/USDT', '1000SATS/USDT', 'ORDI/USDT',
    'MEW/USDT', 'DEGEN/USDT', 'TURBO/USDT', 'MOG/USDT', 'BRETT/USDT',
    'POPCAT/USDT', 'DOGS/USDT',
    'RNDR/USDT', 'FET/USDT', 'ARKM/USDT', 'WLD/USDT',
    'ONDO/USDT', 'PENDLE/USDT', 'TRU/USDT', 
    'ARB/USDT', 'OP/USDT', 'STRK/USDT', 'SUI/USDT', 'SEI/USDT', 'TIA/USDT', 'INJ/USDT',
    'FTM/USDT', 'KAS/USDT', 'MINA/USDT', 'DYM/USDT', 'ALT/USDT', 'MANTA/USDT', 'XAI/USDT',
    'PYTH/USDT', 'JUP/USDT', 'ZETA/USDT', 'RON/USDT', 'BLUR/USDT', 'JTO/USDT', 'CYBER/USDT',
    'AAVE/USDT', 'MKR/USDT', 'SNX/USDT', 'CRV/USDT', 'LDO/USDT', 'DYDX/USDT'
]

ROUTING_COINS = []

def load_config():
    final_exchanges = DEFAULT_EXCHANGES.copy()
    final_coins = [] 
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                saved_coins = data.get("coins", [])
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
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"exchanges": exchanges, "coins": coins}, f)
        log.info("Config saved.")
    except Exception as e:
        log.error(f"Config save error: {e}")