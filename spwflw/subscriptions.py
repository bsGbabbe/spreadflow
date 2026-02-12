from nicegui import ui
from models import Subscription

# Попытка импорта сессии БД
try:
    from db_session import SessionLocal
except ImportError:
    SessionLocal = None

def get_user_subscription(user_id):
    """Получает активную подписку пользователя из БД"""
    if not SessionLocal:
        return None
        
    session = SessionLocal()
    try:
        sub = session.query(Subscription).filter(
            Subscription.user_id == user_id, 
            Subscription.is_active == True
        ).first()
        return sub
    except Exception as e:
        print(f"Error fetching sub: {e}")
        return None
    finally:
        session.close()

def show_subs_dialog(user):
    """Показывает диалог с информацией о подписке"""
    sub = get_user_subscription(user.id)
    plan_name = sub.plan_name if sub else "FREE"
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-6 rounded-xl shadow-lg'):
        # Заголовок
        with ui.row().classes('w-full items-center justify-between mb-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('diamond', size='md', color='green')
                ui.label('Ваша подписка').classes('text-xl font-black text-slate-800')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense color=slate')

        # Текущий план
        with ui.column().classes('w-full bg-slate-50 p-4 rounded-lg border border-slate-100 mb-6'):
            ui.label('ТЕКУЩИЙ ПЛАН').classes('text-xs font-bold text-slate-400 mb-1')
            ui.label(plan_name).classes('text-3xl font-black text-green-600 tracking-tight')
            
            if sub and sub.end_date:
                ui.label(f"Истекает: {sub.end_date.strftime('%Y-%m-%d')}").classes('text-sm text-slate-500 mt-2')
            else:
                 ui.label("Lifetime / Basic access").classes('text-sm text-slate-500 mt-2')

        # Кнопки действий
        with ui.column().classes('w-full gap-2'):
            # === ИСПРАВЛЕНИЕ: используем navigate.to ===
            ui.button('Улучшить тариф', on_click=lambda: ui.navigate.to('/tariffs')).classes('w-full font-bold shadow-md bg-slate-800 text-white')
            ui.button('Управление счетами', on_click=lambda: ui.notify('Функция в разработке')).props('flat color=slate').classes('w-full')

    dialog.open()