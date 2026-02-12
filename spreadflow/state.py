from dataclasses import dataclass, field
from typing import List, Dict
from config import DEFAULT_EXCHANGES

# Настройки по умолчанию
DEFAULT_INVESTMENT = 1000  
DEFAULT_SPREAD_RANGE = {'min': 0.5, 'max': 20.0}

@dataclass
class UserState:
    """
    Личное состояние пользователя.
    """
    investment: float = DEFAULT_INVESTMENT
    
    spread_range: Dict[str, float] = field(default_factory=lambda: DEFAULT_SPREAD_RANGE.copy())
    
    # === НОВОЕ: Фильтр по Market Cap ===
    filter_mcap_enabled: bool = False
    min_mcap: int = 100000000 # По дефолту 100М, если включено
    
    selected_exchanges: List[str] = field(default_factory=lambda: DEFAULT_EXCHANGES.copy())
    
    selected_coins: List[str] = field(default_factory=list) 
    
    is_running: bool = True