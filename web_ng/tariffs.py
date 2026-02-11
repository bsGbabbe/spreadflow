from crud import get_plan_rules, get_db, get_user_by_username, get_user_active_sub
from config import DEFAULT_COINS, DEFAULT_EXCHANGES

# Статичные списки (пока оставляем так)
COINS_BASIC = ['BTC/USDT', 'ETH/USDT']
COINS_STANDARD = DEFAULT_COINS[:20] 
COINS_ALL = DEFAULT_COINS 
EXCHANGES_ALL = DEFAULT_EXCHANGES

def get_user_limits(plan_name_arg=None):
    """
    Умная функция: 
    1. Ищет юзера в сессии.
    2. Достает его подписку.
    3. Если есть 'custom_overrides' — применяет их поверх тарифа.
    """
    from nicegui import app
    
    db = next(get_db())
    limits = {
        "max_spread": 1, "refresh_rate": 30, "blur_hidden": True, 
        "coins": COINS_BASIC, "exchanges": DEFAULT_EXCHANGES[:3],
        "allow_click_links": False
    }

    try:
        username = app.storage.user.get('username')
        plan_name = "FREE"
        overrides = {}

        if username:
            user = get_user_by_username(db, username)
            if user:
                sub = get_user_active_sub(db, user.id)
                if sub:
                    plan_name = sub.plan_name
                    if sub.custom_overrides:
                        overrides = sub.custom_overrides

        # 1. Берем базовые правила тарифа
        base_rules = get_plan_rules(db, plan_name)
        limits.update(base_rules)
        
        # 2. Настраиваем списки монет (Hardcode логика для списков)
        if plan_name == 'FREE': limits['coins'] = COINS_BASIC
        elif plan_name == 'START': limits['coins'] = COINS_STANDARD
        else: limits['coins'] = COINS_ALL
        limits['exchanges'] = EXCHANGES_ALL

        # 3. ПРИМЕНЯЕМ ОВЕРРАЙДЫ (Самое важное!)
        # Если админ задал личный лимит — он перезаписывает тариф
        if overrides:
            if 'max_spread' in overrides: limits['max_spread'] = int(overrides['max_spread'])
            if 'refresh_rate' in overrides: limits['refresh_rate'] = int(overrides['refresh_rate'])
            if 'allow_click_links' in overrides: limits['allow_click_links'] = bool(overrides['allow_click_links'])

        return limits

    except Exception as e:
        print(f"Tariff Error: {e}")
        return limits
    finally:
        db.close()