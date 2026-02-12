from crud import get_db, get_user_by_username, get_user_active_sub, get_plan_by_name
from config import DEFAULT_COINS, DEFAULT_EXCHANGES

# Настройки по умолчанию, если в базе данных ничего не найдено
DEFAULT_CONFIG = {
    "max_spread": 1,
    "coins_limit": 2,      # Лимит количества монет
    "exchanges_limit": 3,  # Лимит количества бирж
    "refresh_rate": 30,
    "blur_hidden": True,
    "allow_click_links": False
}

def get_user_limits(plan_name_arg=None):
    """
    Динамическая система лимитов:
    1. Проверяет роль (Админ получает всё).
    2. Загружает конфиг активного тарифа из БД.
    3. Применяет индивидуальные оверрайды пользователя.
    """
    from nicegui import app
    
    db = next(get_db())
    
    # Стартуем с базовых ограничений
    final_limits = DEFAULT_CONFIG.copy()

    try:
        username = app.storage.user.get('username')
        if not username: 
            return _apply_dynamic_lists(final_limits)

        user = get_user_by_username(db, username)
        if not user: 
            return _apply_dynamic_lists(final_limits)

        # === 1. ПРОВЕРКА НА АДМИНА (ПОЛНЫЙ ДОСТУП) ===
        if user.role == 'admin':
            return {
                "max_spread": 9999,
                "coins": DEFAULT_COINS,
                "exchanges": DEFAULT_EXCHANGES,
                "refresh_rate": 1,
                "blur_hidden": False,
                "allow_click_links": True,
                "coins_limit": len(DEFAULT_COINS),
                "exchanges_limit": len(DEFAULT_EXCHANGES)
            }

        # === 2. ЗАГРУЗКА КОНФИГА ТАРИФА ИЗ БАЗЫ ДАННЫХ ===
        sub = get_user_active_sub(db, user.id)
        plan_config = {}
        
        if sub:
            # Ищем план по имени, указанному в подписке
            plan = get_plan_by_name(db, sub.plan_name)
            if plan and plan.config:
                plan_config = plan.config.copy()
        else:
            # Если подписки нет, пытаемся найти план FREE
            free_plan = get_plan_by_name(db, "FREE")
            if free_plan and free_plan.config:
                plan_config = free_plan.config.copy()

        # Если нашли конфиг в плане — обновляем лимиты
        if plan_config:
            final_limits.update(plan_config)

        # === 3. ПРИМЕНЕНИЕ ИНДИВИДУАЛЬНЫХ ОВЕРРАЙДОВ ===
        if sub and sub.custom_overrides:
            overrides = sub.custom_overrides
            for key, value in overrides.items():
                if value is not None and value != "":
                    try:
                        # Приведение типов для числовых и логических значений
                        if key in ['max_spread', 'coins_limit', 'exchanges_limit', 'refresh_rate']:
                            final_limits[key] = int(float(value))
                        elif key in ['blur_hidden', 'allow_click_links']:
                            final_limits[key] = bool(value)
                        else:
                            final_limits[key] = value
                    except (ValueError, TypeError):
                        continue

        return _apply_dynamic_lists(final_limits)

    except Exception as e:
        print(f"Tariff Logic Error: {e}")
        return _apply_dynamic_lists(final_limits)
    finally:
        db.close()

def _apply_dynamic_lists(config):
    """
    Вспомогательная функция для нарезки списков монет и бирж 
    на основе числовых лимитов из конфига.
    """
    c_limit = config.get('coins_limit', 2)
    e_limit = config.get('exchanges_limit', 3)
    
    # Нарезаем глобальные списки из config.py согласно лимитам тарифа
    config['coins'] = DEFAULT_COINS[:c_limit]
    config['exchanges'] = DEFAULT_EXCHANGES[:e_limit]
    
    return config