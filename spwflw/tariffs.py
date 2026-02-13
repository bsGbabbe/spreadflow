from crud import get_plan_rules, get_db, get_user_by_username, get_user_active_sub
from config import DEFAULT_COINS, DEFAULT_EXCHANGES

# Статичные списки (базовая логика)
COINS_BASIC = ['BTC/USDT', 'ETH/USDT','ADA/USDT', 'AVAX/USDT']
COINS_STANDARD = DEFAULT_COINS[:6] 
COINS_ALL = DEFAULT_COINS 
EXCHANGES_ALL = DEFAULT_EXCHANGES

def get_user_limits(plan_name_arg=None):
    """
    Умная функция определения лимитов:
    1. Если передан plan_name_arg (тест) - берет его.
    2. Иначе ищет юзера в сессии и его подписку.
    3. Применяет настройки тарифа из БД (get_plan_rules).
    4. Если есть 'custom_overrides' у юзера — накладывает их поверх (GOD MODE).
    """
    from nicegui import app
    
    db = next(get_db())
    
    # Дефолтные значения (на случай сбоев)
    limits = {
        "max_spread": 1, 
        "refresh_rate": 30, 
        "blur_hidden": True, 
        "coins": COINS_BASIC, 
        "exchanges": DEFAULT_EXCHANGES[:3],
        "allow_click_links": False,
        "allow_telegram": False
    }

    try:
        username = app.storage.user.get('username')
        plan_name = "FREE"
        overrides = {}

        # 1. Определяем юзера и план
        if plan_name_arg:
            plan_name = plan_name_arg
        elif username:
            user = get_user_by_username(db, username)
            if user:
                sub = get_user_active_sub(db, user.id)
                if sub:
                    plan_name = sub.plan_name
                    # Вытаскиваем персональные настройки
                    if sub.custom_overrides:
                        overrides = sub.custom_overrides

        # 2. Получаем базовые правила тарифа из БД
        # Функция get_plan_rules теперь возвращает словарь параметров
        base_rules = get_plan_rules(db, plan_name)
        if base_rules:
            limits.update(base_rules)
        
        # 3. Настраиваем списки пар/бирж (Hardcode логика для списков монет)
        if plan_name == 'FREE': limits['coins'] = COINS_BASIC
        elif plan_name == 'START': limits['coins'] = COINS_STANDARD
        else: limits['coins'] = COINS_ALL
        limits['exchanges'] = EXCHANGES_ALL

        # 4. GOD MODE: ПРИМЕНЯЕМ ОВЕРРАЙДЫ
        # Если админ задал личные настройки юзеру, они перезаписывают тариф
        if overrides:
            if 'max_spread' in overrides and overrides['max_spread'] is not None: 
                limits['max_spread'] = int(overrides['max_spread'])
            
            if 'refresh_rate' in overrides and overrides['refresh_rate'] is not None: 
                limits['refresh_rate'] = int(overrides['refresh_rate'])
            
            if 'allow_click_links' in overrides and overrides['allow_click_links'] is not None: 
                limits['allow_click_links'] = bool(overrides['allow_click_links'])
                
            if 'allow_telegram' in overrides and overrides['allow_telegram'] is not None: 
                limits['allow_telegram'] = bool(overrides['allow_telegram'])
                
            if 'blur_hidden' in overrides and overrides['blur_hidden'] is not None: 
                limits['blur_hidden'] = bool(overrides['blur_hidden'])

        return limits

    except Exception as e:
        print(f"Tariff Error: {e}")
        return limits
    finally:
        db.close()