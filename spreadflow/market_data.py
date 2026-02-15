import asyncio
import aiohttp
from logger import log
from config import DEFAULT_COINS  # Предполагаем, что в config есть список монет, если нет - используем дефолтный

# --- ГЛОБАЛЬНОЕ ХРАНИЛИЩЕ ДАННЫХ ---
# Инициализируем пустым словарем, чтобы избежать AttributeError при импорте
GLOBAL_MARKET_DATA = {}

# API CoinGecko (или аналог)
CG_API_URL = "https://api.coingecko.com/api/v3/coins/markets"

async def fetch_market_data():
    """
    Асинхронное получение данных о рынке (цены, капа, объем).
    Использует CoinGecko API.
    """
    global GLOBAL_MARKET_DATA
    
    # Маппинг тикеров для CoinGecko (можно расширить)
    # В реальном проекте лучше хранить это в БД или конфиге
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': 'false'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CG_API_URL, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Преобразуем список в словарь для быстрого доступа по символу
                    new_data = {}
                    for item in data:
                        symbol = item['symbol'].upper() + '/USDT' # Приводим к формату бирж
                        new_data[symbol] = {
                            'price': item.get('current_price', 0),
                            'market_cap': item.get('market_cap', 0),
                            'total_volume': item.get('total_volume', 0),
                            'price_change_24h': item.get('price_change_percentage_24h', 0),
                            'image': item.get('image', ''),
                            'name': item.get('name', '')
                        }
                    
                    GLOBAL_MARKET_DATA = new_data
                    log.info(f"✅ Market Data Updated: {len(GLOBAL_MARKET_DATA)} coins")
                else:
                    log.warning(f"⚠️ Market Data API Error: {response.status}")
                    
    except Exception as e:
        log.error(f"❌ Market Data Fetch Error: {e}")

async def market_service_task():
    """
    Фоновая задача, которая обновляет данные раз в 60 секунд.
    """
    log.info("🚀 Market Data Service Started")
    while True:
        await fetch_market_data()
        await asyncio.sleep(60) # Лимиты CoinGecko Free - аккуратнее с частотой