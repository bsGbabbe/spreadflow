import asyncio
import requests
from nicegui import run
from logger import log

# Глобальное хранилище
MARKET_DATA = []

def fetch_coingecko_sync():
    """Забирает данные о рынке (Топ 150)"""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 150, # <--- Увеличили до 150
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            log.info(f"📉 Market Data Updated: {len(data)} coins fetched")
            return data
        else:
            log.error(f"📉 Market Data Failed: Status {response.status_code}")
    except Exception as e:
        log.error(f"📉 Market Data Error: {e}")
    return []

async def market_service_task():
    global MARKET_DATA
    log.info("📉 Market Data Service Started")
    
    # Сразу при старте пробуем скачать
    data = await run.io_bound(fetch_coingecko_sync)
    if data: MARKET_DATA = data

    while True:
        try:
            await asyncio.sleep(120) 
            data = await run.io_bound(fetch_coingecko_sync)
            if data:
                MARKET_DATA = data
        except Exception as e:
            log.error(f"Market Loop Error: {e}")
            await asyncio.sleep(60)