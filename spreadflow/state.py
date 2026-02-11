from dataclasses import dataclass, field
from typing import List

# Глобальные настройки по умолчанию (для сброса)
DEFAULT_INVESTMENT = 0     
DEFAULT_SPREAD = 0.0       

@dataclass
class UserState:
    """
    Личное состояние пользователя (фильтры).
    Создается новое для каждой сессии браузера.
    """
    investment: float = DEFAULT_INVESTMENT
    target_spread: float = DEFAULT_SPREAD
    
    # Списки выбранных бирж и монет
    selected_exchanges: List[str] = field(default_factory=list)
    selected_coins: List[str] = field(default_factory=list)
    
    # Флаг: включил ли пользователь отображение у себя
    is_running: bool = False