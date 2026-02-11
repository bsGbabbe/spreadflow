import asyncio
import requests
from nicegui import run
from logger import log

# Глобальное хранилище данных рынка (Топ-100)
MARKET_DATA = []

def fetch_coingecko_sync():
    """Забирает данные о рынке (Топ 100) одним запросом"""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }
    # User-Agent важен, чтобы не получить бан
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        log.error(f"Market Data Error: {e}")
    return []

async def market_service_task():
    """Фоновая задача: обновляет данные рынка раз в 2 минуты"""
    global MARKET_DATA
    log.info("📉 Market Data Service Started")
    
    while True:
        try:
            # Запускаем в отдельном потоке, чтобы не блокировать интерфейс
            data = await run.io_bound(fetch_coingecko_sync)
            if data:
                MARKET_DATA = data
            
            # Ждем 120 секунд (ограничение бесплатного API CoinGecko)
            await asyncio.sleep(120) 
        except Exception as e:
            log.error(f"Market Loop Error: {e}")
            await asyncio.sleep(60)