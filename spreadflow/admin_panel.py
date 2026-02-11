from db_session import SessionLocal
from models import Invite

def create_invite():
    print("\n--- ГЕНЕРАТОР ИНВАЙТОВ (POSTGRESQL) ---")
    
    code = input("Придумайте код (напр. START_2024): ").strip()
    if not code: return

    print("Выберите тариф:")
    print("1. START")
    print("2. PRO")
    print("3. WHALE")
    choice = input("Ваш выбор (1-3): ")
    
    plan_map = {'1': 'START', '2': 'PRO', '3': 'WHALE'}
    plan = plan_map.get(choice, 'PRO')
    
    limit = input("Сколько человек могут использовать? [Enter = 100]: ")
    if not limit: limit = 100
    else: limit = int(limit)

    # Запись в базу
    db = SessionLocal()
    try:
        new_invite = Invite(code=code, plan_name=plan, usage_limit=limit)
        db.add(new_invite)
        db.commit()
        print(f"\n✅ УСПЕХ! Код '{code}' создан.")
        print(f"🎁 Тариф: {plan}")
        print(f"👥 Лимит: {limit} активаций")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    while True:
        create_invite()
        if input("\nСоздать еще? (y/n): ").lower() != 'y': break