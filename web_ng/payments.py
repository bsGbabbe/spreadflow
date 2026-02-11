import os
import requests
import json
from dotenv import load_dotenv

# --- НАСТРОЙКА И БЕЗОПАСНОСТЬ ---
# 1. Загружаем переменные из файла .env
load_dotenv()

# 2. Получаем ключи из окружения
# Если ключей нет, скрипт предупредит об этом в консоли
SHOP_ID = os.getenv("CRYPTO_SHOP_ID")
API_KEY = os.getenv("CRYPTO_API_KEY")
SECRET_KEY = os.getenv("CRYPTO_SECRET_KEY")

if not SHOP_ID or not API_KEY:
    print("⚠️  ВНИМАНИЕ: Не найдены ключи CryptoCloud в файле .env!")
    print("Создайте файл .env и добавьте туда CRYPTO_SHOP_ID и CRYPTO_API_KEY")

# Базовый URL API CryptoCloud
BASE_URL = "https://api.cryptocloud.plus/v1"

# --- ФУНКЦИИ ---

def create_crypto_invoice(amount_usd, order_id, email=None):
    # ... (код заголовков и payload тот же) ...
    url = f"{BASE_URL}/invoice/create"
    
    headers = {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "shop_id": SHOP_ID,
        "amount": amount_usd,
        "currency": "USD",
        "order_id": order_id,
        "email": email
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Сервер возвращает данные сразу, без обертки "result"
        if response.status_code == 200 and data.get("status") == "success":
            return {
                "success": True,
                # Берем ключи напрямую из ответа (как в вашем логе)
                "pay_url": data["pay_url"],      
                "invoice_id": data["invoice_id"] 
            }
        else:
            error_msg = data.get("msg", str(data))
            print(f"❌ API Error: {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
        return {"success": False, "error": str(e)}

def check_crypto_status(invoice_uuid):
    """
    Проверяет статус счета.
    Финальная версия под API v2 (поле status_invoice).
    """
    url = f"{BASE_URL}/invoice/info"
    
    params = {"uuid": invoice_uuid}
    
    headers = {
        "Authorization": f"Token {API_KEY}"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        # --- ФИНАЛЬНАЯ ЛОГИКА ---
        # Мы точно знаем, что статус лежит в поле 'status_invoice'
        status_raw = data.get("status_invoice")
        
        if status_raw in ["paid", "overpaid"]:
            return "PAID"     # Деньги пришли! Выдаем доступ.
            
        elif status_raw == "partial":
            return "PARTIAL"  # Прислали мало денег.
            
        elif status_raw == "canceled":
            return "CANCELED" # Счет отменен или истек таймер.
            
        else:
            # Сюда попадает 'created' и 'process'
            return "WAITING"  # Ждем поступления средств.
        
    except Exception as e:
        print(f"Check Status Error: {e}")
        return "ERROR"