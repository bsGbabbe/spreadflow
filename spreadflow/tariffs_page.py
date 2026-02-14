from nicegui import ui, app
import time
import asyncio

# Импорты наших модулей
from crud import get_db, upgrade_user_plan, get_all_plans
from payments import create_crypto_invoice, check_crypto_status

def create_tariffs_route():
    @ui.page('/tariffs')
    def tariffs_page():
        # --- СТИЛИ CSS ---
        ui.add_head_html('''
        <style>
            body { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
            
            /* Карточка тарифа */
            .pricing-card { 
                transition: all 0.3s ease; 
                border: 1px solid #e2e8f0; 
                border-radius: 16px;
                display: flex;
                flex-direction: column;
            }
            .pricing-card:hover { 
                transform: translateY(-5px); 
                box-shadow: 0 15px 30px rgba(0,0,0,0.1); 
            }
            
            /* Типографика */
            .price-tag { font-size: 36px; font-weight: 800; color: #0f172a; }
            .plan-name { font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
            
            /* Галочки */
            .check-icon { color: #16a34a; font-weight: bold; margin-right: 6px; }
            .feature-text { font-size: 14px; color: #475569; font-weight: 500; }
            
            /* Стили для темной темы (Whale) */
            .dark-card .price-tag { color: white; }
            .dark-card .feature-text { color: #cbd5e1; }
        </style>
        ''')

        # --- HEADER ---
        with ui.header().classes('bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('arrow_back', color='black').classes('cursor-pointer hover:bg-gray-100 rounded-full p-1').on('click', lambda: ui.navigate.to('/'))
                ui.label('Назад в терминал').classes('text-sm font-bold text-gray-500 cursor-pointer hover:text-black').on('click', lambda: ui.navigate.to('/'))
            ui.label('ВЫБОР ТАРИФА').classes('text-lg font-black text-gray-900 tracking-tight')
            ui.element('div').classes('w-24') # Распорка для центровки

        # --- ЛОГИКА ПОКУПКИ (CRYPTO CLOUD) ---
        async def buy_plan(plan_name, price_str):
            # 1. Проверка авторизации
            user_id = app.storage.user.get('user_id')
            
            if not user_id:
                ui.notify('Сначала войдите в аккаунт!', type='warning')
                ui.navigate.to('/login')
                return

            # 2. Парсинг цены (превращаем "$40" -> 40.0)
            try:
                clean_price = price_str.replace('$', '').replace(' ', '')
                amount = float(clean_price)
            except:
                ui.notify('Ошибка цены тарифа. Обратитесь в поддержку.', type='negative')
                return

            # Если цена 0 (FREE), просто переключаем
            if amount <= 0:
                db = next(get_db())
                upgrade_user_plan(db, user_id, plan_name)
                db.close()
                ui.notify(f'Тариф {plan_name} активирован!', type='positive')
                ui.navigate.to('/profile')
                return

            # 3. Показываем спиннер
            loading_notif = ui.notify('Генерируем ссылку на оплату...', type='ongoing', timeout=0)
            
            # --- ЗАПРОС К CRYPTOCLOUD (Асинхронно) ---
            # ИСПРАВЛЕНИЕ: Передаем правильные аргументы (user_id, plan_name, amount)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: create_crypto_invoice(user_id, plan_name, amount))
            
            # Безопасно убираем уведомление
            if loading_notif:
                try:
                    loading_notif.dismiss()
                except:
                    pass

            if result['success']:
                pay_url = result['pay_url']
                invoice_id = result['invoice_id']
                
                # --- ДИАЛОГ ОПЛАТЫ ---
                with ui.dialog() as pay_dialog, ui.card().classes('w-full max-w-md items-center p-8'):
                    ui.icon('verified_user', size='lg', color='green-500').classes('mb-2')
                    ui.label(f'Оплата тарифа {plan_name}').classes('text-2xl font-black mb-1')
                    ui.label(f'Сумма к оплате: ${amount}').classes('text-lg text-gray-500 mb-6 font-mono')
                    
                    ui.label('1. Нажмите кнопку для оплаты (USDT / Карта):').classes('text-sm font-bold self-start mb-2')
                    
                    # ui.navigate.to вместо ui.open для корректного открытия в новой вкладке
                    ui.button('ПЕРЕЙТИ К ОПЛАТЕ ➔', on_click=lambda: ui.navigate.to(pay_url, new_tab=True)).props('unelevated color=blue-600 size=lg').classes('w-full font-bold mb-6')
                    
                    ui.separator().classes('mb-6')
                    
                    ui.label('2. После оплаты нажмите кнопку проверки:').classes('text-sm font-bold self-start mb-2')

                    # Функция проверки статуса
                    async def check_payment():
                        chk_notif = ui.notify('Связываемся с блокчейном...', type='ongoing')
                        
                        # Запрос к API статуса
                        status = await loop.run_in_executor(None, lambda: check_crypto_status(invoice_id))
                        
                        if chk_notif:
                            try:
                                chk_notif.dismiss()
                            except:
                                pass
                        
                        if status == "PAID":
                            pay_dialog.close()
                            
                            # Активируем тариф в базе
                            db = next(get_db())
                            ok, msg = upgrade_user_plan(db, user_id, plan_name)
                            db.close()
                            
                            if ok:
                                ui.notify(f'УСПЕШНО! Вы теперь {plan_name}!', type='positive', close_button=True, timeout=10000)
                                ui.navigate.to('/profile')
                            else:
                                ui.notify(f'Оплата прошла, но ошибка базы: {msg}', type='negative')
                                
                        elif status == "WAITING":
                            ui.notify('Оплата еще не поступила. Подождите 1-2 минуты.', type='warning')
                        elif status == "PARTIAL":
                            ui.notify('Внимание: Частичная оплата! Напишите в поддержку.', type='warning')
                        elif status == "CANCELED":
                            ui.notify('Счет был отменен.', type='negative')
                        else:
                            ui.notify(f'Ошибка проверки: {status}', type='negative')

                    ui.button('Я ОПЛАТИЛ, ПРОВЕРИТЬ', on_click=check_payment).props('outline color=green').classes('w-full font-bold')
                    
                    # Кнопка закрытия
                    ui.button('Отмена', on_click=pay_dialog.close).props('flat color=grey small').classes('mt-4')

                pay_dialog.open()
                
            else:
                # Если API вернуло ошибку
                error_text = result.get('error', 'Unknown Error')
                ui.notify(f"Ошибка создания счета: {error_text}", type='negative', close_button=True, timeout=10000)


        # --- ЗАГРУЗКА ДАННЫХ ---
        # Получаем тарифы из базы данных
        db = next(get_db())
        plans_list = get_all_plans(db)
        db.close()

        # Сортировка: START -> PRO -> WHALE
        sort_order = {'START': 1, 'PRO': 2, 'WHALE': 3}
        
        # Фильтруем (убираем FREE и скрытые тарифы)
        display_plans = sorted(
            [p for p in plans_list if p.name in sort_order and p.is_public], 
            key=lambda x: sort_order.get(x.name, 99)
        )

        # --- UI КОНТЕНТ ---
        with ui.column().classes('w-full max-w-6xl mx-auto p-8 gap-8 items-center'):
            
            # Заголовки
            with ui.column().classes('items-center gap-2 mb-4'):
                ui.label('Инвестируйте в скорость').classes('text-4xl font-black text-slate-900 text-center tracking-tight')
                ui.label('Выберите план, который подходит вашему стилю торговли').classes('text-lg text-gray-500 text-center font-medium')

            # Сетка карточек
            with ui.row().classes('w-full justify-center gap-8 items-stretch wrap'):
                
                for p in display_plans:
                    
                    # ОПРЕДЕЛЕНИЕ СТИЛЕЙ ПО ТИПУ ТАРИФА
                    is_pro = (p.name == 'PRO')
                    is_whale = (p.name == 'WHALE')
                    
                    # Базовые классы
                    card_classes = 'pricing-card w-80 p-8'
                    btn_classes = 'w-full mt-auto py-3 font-bold rounded-lg shadow-none transition-colors'
                    
                    if is_pro:
                        # PRO: Зеленая обводка, увеличен, тень
                        card_classes += ' border-2 border-green-500 relative transform scale-105 shadow-xl bg-white'
                        btn_props = 'unelevated color=green-6 text-color=white'
                        price_color = 'text-green-600'
                    elif is_whale:
                        # WHALE: Темный фон
                        card_classes += ' bg-slate-900 border-slate-800 dark-card text-white'
                        btn_props = 'unelevated color=purple-6 text-color=white'
                        price_color = 'text-purple-400'
                    else:
                        # START: Обычный
                        card_classes += ' bg-white'
                        btn_props = 'flat color=grey-3 text-color=grey-9'
                        price_color = 'text-gray-900'

                    # ОТРИСОВКА КАРТОЧКИ
                    with ui.card().classes(card_classes):
                        
                        if is_pro:
                            ui.label('MOST POPULAR').classes('absolute -top-3 left-1/2 transform -translate-x-1/2 bg-green-500 text-white text-[10px] font-bold px-3 py-1 rounded-full tracking-wider')

                        ui.label(p.name).classes(f'plan-name {price_color}')
                        
                        with ui.row().classes('items-baseline mb-6'):
                            ui.label(p.price_str).classes('price-tag')
                            ui.label(p.period_str).classes('text-gray-400 font-medium text-sm ml-1')
                        
                        ui.separator().classes('mb-6 opacity-50')
                        
                        with ui.column().classes('gap-3 flex-grow mb-8'):
                            if p.description_features:
                                for feature in p.description_features:
                                    with ui.row().classes('items-center gap-0 no-wrap'):
                                        ui.label('✓').classes('check-icon')
                                        ui.label(feature).classes('feature-text')
                            else:
                                ui.label('Standard features').classes('feature-text')

                        # Кнопка действия (Вызывает функцию buy_plan)
                        ui.button(
                            'GET STARTED' if not is_whale else 'BECOME A WHALE', 
                            on_click=lambda n=p.name, pr=p.price_str: buy_plan(n, pr)
                        ).props(btn_props).classes(btn_classes)