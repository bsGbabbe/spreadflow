from config import load_config

# Загружаем настройки при старте
saved_exs, saved_cns = load_config()

# Глобальный словарь состояния
app_state = {
    "is_running": True,      # АВТО-СТАРТ
    "data": [],              # Результаты сканирования
    "last_update_ts": 0,     # Время обновления данных (Backend)
    "ui_updated_ts": 0,      # Время обновления UI (Frontend)
    "selected_symbol": None,
    "loops": 1.0,
    "history": {},           
    
    # Настройки калькулятора и фильтров
    "investment": 1000.0,
    "target_spread": 0.1,
    "refresh_rate": 3.0,
    "min_volume": 50000.0,
    
    # --- ЛОГИКА ИЗМЕНЕНА ---
    "include_chains": False, # По умолчанию FALSE (Только простые связки)
    # -----------------------
    
    # Статус системы
    "exchanges_ready": False,
    "status_message": "Запуск...",
    
    # Активные фильтры
    "selected_exchanges": saved_exs,
    "selected_coins": saved_cns
}