import requests
import json
import uuid
from config import CRYPTOCLOUD_CONFIG
from crud import get_db, upgrade_user_plan
from models import Payment
from logger import log

# Используем настройки из config.py
SHOP_ID = CRYPTOCLOUD_CONFIG['shop_id']
API_KEY = CRYPTOCLOUD_CONFIG['api_key']
BASE_URL = CRYPTOCLOUD_CONFIG['base_url'] 

# --- ФУНКЦИИ ---

def create_crypto_invoice(user_id, plan_name, amount_usd):
    """
    Создает платеж в БД и ссылку на оплату в CryptoCloud.
    Возвращает словарь, который ожидает frontend.
    """
    order_id = str(uuid.uuid4()) # Генерируем уникальный ID заказа
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
        "email": "user@email.com" 
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        # Проверка успешного ответа
        if response.status_code == 200 and data.get("status") == "success":
            
            # 1. Сохраняем в БД (Pending)
            db = next(get_db())
            try:
                new_payment = Payment(
                    id=order_id,
                    user_id=user_id,
                    amount_usd=amount_usd,
                    plan_name=plan_name,
                    invoice_id=data["invoice_id"], # ID из ответа CryptoCloud
                    status="pending"
                )
                db.add(new_payment)
                db.commit()
            finally:
                db.close()
            
            # 2. Возвращаем словарь (ВАЖНО: Frontend ждет именно dict, а не строку)
            return {
                "success": True,
                "pay_url": data["pay_url"],
                "invoice_id": data["invoice_id"]
            }
            
        else:
            error_msg = data.get("msg", str(data))
            log.error(f"❌ API Error: {error_msg}")
            return {"success": False, "error": error_msg}

    except Exception as e:
        log.error(f"❌ Payment Creation Error: {str(e)}")
        return {"success": False, "error": str(e)}

def check_crypto_status(invoice_id):
    """
    Проверяет статус счета через API.
    """
    url = f"{BASE_URL}/invoice/info"
    
    payload = {"uuid": invoice_id}
    headers = {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        
        status_raw = data.get("status_invoice")
        
        if status_raw in ["paid", "overpaid"]:
            return "PAID"
        elif status_raw == "partial":
            return "PARTIAL"
        elif status_raw == "canceled":
            return "CANCELED"
        else:
            return "WAITING"
            
    except Exception as e:
        log.error(f"Check Status Error: {e}")
        return "ERROR"

async def process_webhook(data):
    """
    Обработка уведомления от CryptoCloud.
    """
    webhook_status = data.get('status')
    invoice_id = data.get('invoice_id')
    order_id = data.get('order_id')

    log.info(f"Webhook received: Order {order_id}, Status {webhook_status}")

    if webhook_status != 'paid' and webhook_status != 'success':
        return False

    # === ЭТАП БЕЗОПАСНОСТИ: ОБРАТНАЯ ПРОВЕРКА ===
    real_status = check_crypto_status(invoice_id)
    
    if real_status != "PAID":
        log.warning(f"⚠️ Security Alert: Webhook says PAID, but API says {real_status}. Ignoring.")
        return False

    # === ЕСЛИ ПРОВЕРКА ПРОЙДЕНА -> ВЫДАЕМ ПОДПИСКУ ===
    db = next(get_db())
    try:
        payment = db.query(Payment).filter(Payment.id == order_id).first()
        
        if not payment:
            log.error(f"Payment record not found: {order_id}")
            return False

        if payment.status != 'paid':
            # 1. Обновляем статус платежа
            payment.status = 'paid'
            
            # 2. Выдаем подписку
            upgrade_user_plan(db, payment.user_id, payment.plan_name)
            
            db.commit()
            log.info(f"✅ Subscription UPGRADED for user {payment.user_id} (Plan: {payment.plan_name})")
            return True
        else:
            log.info(f"Payment {order_id} already processed.")
            return True

    except Exception as e:
        db.rollback()
        log.error(f"Database error in webhook: {e}")
        return False
    finally:
        db.close()