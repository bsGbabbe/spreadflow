from dataclasses import dataclass, field
from typing import List, Dict
from config import DEFAULT_EXCHANGES

# Настройки по умолчанию
DEFAULT_INVESTMENT = 1000  
# Диапазон спреда: от 0.5% до 20%
DEFAULT_SPREAD_RANGE = {'min': 0.1, 'max': 999.0}

@dataclass
class UserState:
    """
    Личное состояние пользователя.
    """
    investment: float = DEFAULT_INVESTMENT
    
    # === ИЗМЕНЕНИЕ: Теперь храним MIN и MAX ===
    spread_range: Dict[str, float] = field(default_factory=lambda: DEFAULT_SPREAD_RANGE.copy())
    
    # Биржи берем из конфига
    selected_exchanges: List[str] = field(default_factory=lambda: DEFAULT_EXCHANGES.copy())
    
    # Список монет
    selected_coins: List[str] = field(default_factory=list) 
    
    is_running: bool = True