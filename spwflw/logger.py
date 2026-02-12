import logging
import sys

def setup_logger():
    """Настройка красивого вывода в консоль"""
    logger = logging.getLogger("SpreadFlow")
    logger.setLevel(logging.INFO)
    
    # Формат: [ВРЕМЯ] [УРОВЕНЬ] Сообщение
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    
    # Чтобы не дублировались логи при перезагрузке
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

log = setup_logger()