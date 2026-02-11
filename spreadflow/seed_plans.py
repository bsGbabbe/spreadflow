from db_session import SessionLocal
from models import Plan

def seed_plans():
    db = SessionLocal()
    
    # Данные наших тарифов
    plans_data = [
        {
            "name": "FREE", "price_str": "$0", "period_str": "/ forever", "css_color": "gray",
            "features": ["Только BTC/ETH", "Спреды до 1%", "Обновление 30 сек", "Без уведомлений"],
            "max_spread": 1, "refresh_rate": 30, "blur_hidden": True, "allow_click_links": False
        },
        {
            "name": "START", "price_str": "$15", "period_str": "/ week", "css_color": "blue",
            "features": ["Топ-20 монет", "Спреды до 3%", "Обновление 15 сек", "Без уведомлений"],
            "max_spread": 3, "refresh_rate": 15, "blur_hidden": True, "allow_click_links": False
        },
        {
            "name": "PRO", "price_str": "$40", "period_str": "/ week", "css_color": "green",
            "features": ["Все монеты (100+)", "Спреды до 10%", "Обновление 3 сек", "Telegram сигналы"],
            "max_spread": 10, "refresh_rate": 3, "blur_hidden": True, "allow_click_links": False
        },
        {
            "name": "WHALE", "price_str": "$99", "period_str": "/ week", "css_color": "purple",
            "features": ["Полный доступ", "Безлимитные спреды", "Real-time (1 сек)", "Ссылки на биржи"],
            "max_spread": 9999, "refresh_rate": 1, "blur_hidden": False, "allow_click_links": True
        }
    ]

    for p in plans_data:
        # Проверяем, есть ли уже такой план
        existing = db.query(Plan).get(p["name"])
        if not existing:
            new_plan = Plan(
                name=p["name"], price_str=p["price_str"], period_str=p["period_str"],
                css_color=p["css_color"], description_features=p["features"],
                max_spread=p["max_spread"], refresh_rate=p["refresh_rate"],
                blur_hidden=p["blur_hidden"], allow_click_links=p["allow_click_links"]
            )
            db.add(new_plan)
            print(f"Создан тариф: {p['name']}")
        else:
            print(f"Тариф {p['name']} уже есть")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    seed_plans()