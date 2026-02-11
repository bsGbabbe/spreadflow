from nicegui import ui, app
from fastapi.responses import RedirectResponse
from state import UserState
import backend
import tariffs
import user_profile
import admin_panel
import auth
import subscriptions
import time
from config import DEFAULT_EXCHANGES, DEFAULT_COINS
from market_data import MARKET_DATA

def init_ui():
    @ui.page('/')
    def main_page():
        # === БЕЗОПАСНОСТЬ: Редирект, если не залогинен ===
        user = auth.get_current_user()
        if not user:
            return RedirectResponse('/login')

        # === ЛИЧНОЕ СОСТОЯНИЕ (Фильтры) ===
        state = UserState()
        last_render_ts = 0

        # === СТИЛИ ===
        ui.add_head_html('''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap');
            body { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
            .mono { font-family: 'Roboto Mono', monospace; }
            .coin-row:hover { background: #f1f5f9; cursor: pointer; }
            .pos-change { color: #16a34a; font-weight: 600; }
            .neg-change { color: #dc2626; font-weight: 600; }
        </style>
        ''')

        # === SIDEBAR (Меню слева) ===
        with ui.left_drawer(value=True).classes('bg-white border-r border-gray-200 p-6 flex flex-col gap-6 shadow-sm'):
            ui.label("SPREADFLOW").classes('text-2xl font-black text-slate-800 tracking-tighter')
            
            # Профиль
            with ui.row().classes('items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100'):
                ui.avatar('person', color='slate-300', text_color='white').classes('shadow-sm')
                with ui.column().classes('gap-0'):
                    ui.label(user.username).classes('font-bold text-slate-700 text-sm')
                    ui.label(user.role).classes('text-xs text-slate-400 uppercase font-bold')

            ui.separator().classes('bg-slate-100')

            # Управление сканером (Личное!)
            with ui.column().classes('gap-2'):
                ui.label("PERSONAL SCANNER").classes('text-xs font-bold text-slate-400 mb-1')
                status_label = ui.label('IDLE').classes('text-xs font-bold text-slate-400')
                btn_start = ui.button('START').classes('w-full font-bold shadow-md transition-all')
                
                def toggle_start():
                    state.is_running = not state.is_running
                    update_start_btn()
                    if state.is_running: render_arbitrage() 

                def update_start_btn():
                    if state.is_running:
                        btn_start.props('color=red icon=stop label="STOP"')
                        status_label.set_text("● ONLINE")
                        status_label.classes(replace='text-green-500')
                    else:
                        btn_start.props('color=slate icon=rocket label="START"')
                        status_label.set_text("● PAUSED")
                        status_label.classes(replace='text-slate-400')
                
                btn_start.on_click(toggle_start)
                update_start_btn()

            ui.separator().classes('bg-slate-100')
            
            # Кнопки навигации
            with ui.column().classes('w-full gap-2'):
                ui.button('Profile', icon='settings', on_click=lambda: user_profile.show_profile_dialog(user)).props('flat align=left color=slate').classes('w-full')
                ui.button('Subscriptions', icon='diamond', on_click=lambda: subscriptions.show_subs_dialog(user)).props('flat align=left color=slate').classes('w-full')
                if user.role == 'admin':
                    ui.button('Admin Panel', icon='admin_panel_settings', on_click=lambda: admin_panel.show_admin_dialog(user)).props('flat align=left color=red').classes('w-full')
                ui.button('Logout', icon='logout', on_click=lambda: auth.logout()).props('flat align=left color=slate').classes('w-full')

        # === ЦЕНТРАЛЬНАЯ ЧАСТЬ (Tabs) ===
        with ui.column().classes('w-full p-6 max-w-7xl mx-auto gap-6'):
            
            with ui.tabs().classes('w-full text-slate-600') as tabs:
                tab_arb = ui.tab('ARBITRAGE', icon='bolt')
                tab_market = ui.tab('MARKET OVERVIEW', icon='bar_chart')
            
            with ui.tab_panels(tabs, value=tab_arb).classes('w-full bg-transparent'):
                
                # --- Вкладка 1: АРБИТРАЖ ---
                with ui.tab_panel(tab_arb).classes('p-0 gap-4'):
                    
                    # Панель фильтров
                    with ui.expansion('⚙️ Filters & Investment', icon='tune').classes('w-full bg-white rounded-xl shadow-sm border border-slate-200 mb-4'):
                        with ui.column().classes('p-4 w-full'):
                            with ui.row().classes('w-full gap-6 mb-4'):
                                with ui.column().classes('flex-1'):
                                    ui.label("Invest ($)").classes('text-xs font-bold text-slate-400')
                                    ui.number(min=0).bind_value(state, 'investment').classes('w-full')
                                with ui.column().classes('flex-1'):
                                    ui.label("Min Spread (%)").classes('text-xs font-bold text-slate-400')
                                    ui.slider(min=0.0, max=10.0, step=0.1).bind_value(state, 'target_spread').classes('w-full')
                                    ui.label().bind_text_from(state, 'target_spread', lambda x: f"{x}%").classes('text-xs font-bold text-slate-600')

                            ui.separator().classes('mb-4')
                            
                            with ui.row().classes('w-full gap-6'):
                                with ui.column().classes('flex-1'):
                                    ui.label("Exchanges").classes('text-xs font-bold text-slate-400')
                                    ui.select(DEFAULT_EXCHANGES, multiple=True, label="Select Exchanges").bind_value(state, 'selected_exchanges').classes('w-full')
                                
                                with ui.column().classes('flex-1'):
                                    ui.label("Coins").classes('text-xs font-bold text-slate-400')
                                    ui.select(DEFAULT_COINS, multiple=True, label="Select Coins").bind_value(state, 'selected_coins').classes('w-full')

                    # Таблица арбитража
                    ui.label("LIVE OPPORTUNITIES").classes('text-xl font-black text-slate-800 tracking-tight')
                    grid_cls = 'grid grid-cols-[1.5fr_1fr_1fr_1fr_1fr_2fr] gap-4 items-center px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider'
                    with ui.row().classes(f'w-full bg-slate-100 rounded-lg {grid_cls}'):
                        ui.label('PAIR'); ui.label('SPREAD'); ui.label('PROFIT'); ui.label('BUY'); ui.label('SELL'); ui.label('ROUTE')

                    arb_container = ui.column().classes('w-full gap-2')

                    def render_arbitrage():
                        # Если выключено или не выбраны фильтры - чистим и выходим
                        if not state.is_running:
                            arb_container.clear()
                            with arb_container:
                                ui.label("Scanner is PAUSED. Configure filters and press START.").classes('w-full text-center text-slate-400 py-8 italic')
                            return
                        
                        if not state.selected_exchanges or not state.selected_coins:
                            arb_container.clear()
                            with arb_container:
                                ui.label("⚠️ Please select at least one Exchange and Coin.").classes('w-full text-center text-amber-500 py-8 font-bold')
                            return

                        arb_container.clear()
                        
                        # === ФИЛЬТРАЦИЯ ДАННЫХ ===
                        # Берем ОБЩИЕ данные из backend и фильтруем под ЮЗЕРА
                        user_opportunities = []
                        for item in backend.GLOBAL_OPPORTUNITIES:
                            if item['symbol'] not in state.selected_coins: continue
                            if item['buy_ex'] not in state.selected_exchanges: continue
                            if item['sell_ex'] not in state.selected_exchanges: continue
                            if item['spread'] < state.target_spread: continue
                            
                            # Считаем личный профит
                            profit = (item['spread'] / 100.0) * state.investment
                            display_item = item.copy()
                            display_item['profit'] = profit
                            user_opportunities.append(display_item)

                        if not user_opportunities:
                            with arb_container:
                                ui.label("No opportunities match your filters.").classes('w-full text-center text-slate-400 py-8')
                            return

                        # Рендер списка (топ 30)
                        for item in user_opportunities[:30]:
                            with arb_container:
                                with ui.row().classes('w-full bg-white p-4 rounded-xl shadow-sm border border-slate-100 items-center grid grid-cols-[1.5fr_1fr_1fr_1fr_1fr_2fr] gap-4 transition-all hover:shadow-md'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.avatar(item['symbol'][0], color='slate-100', text_color='slate-700').classes('text-sm font-bold')
                                        ui.label(item['symbol']).classes('font-bold text-slate-700')
                                    
                                    color = 'text-green-600' if item['spread'] > 1.0 else 'text-amber-600'
                                    ui.label(f"{item['spread']:.2f}%").classes(f'text-lg font-black mono {color}')
                                    ui.label(f"${item['profit']:.2f}").classes('text-slate-600 font-bold mono')
                                    ui.label(f"{item['buy_price']}").classes('text-xs text-slate-400 mono')
                                    ui.label(f"{item['sell_price']}").classes('text-xs text-slate-400 mono')
                                    with ui.row().classes('items-center gap-2'):
                                        ui.badge(item['buy_ex'], color='slate-100').props('text-color=black')
                                        ui.icon('arrow_forward', size='xs', color='slate-300')
                                        ui.badge(item['sell_ex'], color='green-100').props('text-color=green-800')

                # --- Вкладка 2: РЫНОК (CMC Style) ---
                with ui.tab_panel(tab_market).classes('p-0 gap-4'):
                    ui.label("MARKET OVERVIEW (Top 100)").classes('text-xl font-black text-slate-800 tracking-tight')
                    
                    market_grid = 'grid grid-cols-[50px_3fr_2fr_2fr_2fr_2fr] gap-4 items-center px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider'
                    with ui.row().classes(f'w-full bg-slate-100 rounded-lg {market_grid}'):
                        ui.label('#'); ui.label('COIN'); ui.label('PRICE'); ui.label('24h %'); ui.label('MCAP'); ui.label('VOL')
                    
                    market_container = ui.column().classes('w-full gap-1')
                    
                    def render_market():
                        market_container.clear()
                        if not MARKET_DATA:
                            with market_container: ui.spinner('dots', size='lg', color='green')
                            return
                        
                        for coin in MARKET_DATA:
                            with market_container:
                                with ui.row().classes('w-full bg-white px-4 py-3 rounded-lg border-b border-slate-100 items-center grid grid-cols-[50px_3fr_2fr_2fr_2fr_2fr] gap-4 coin-row'):
                                    ui.label(str(coin['market_cap_rank'])).classes('text-slate-400 mono text-xs')
                                    with ui.row().classes('items-center gap-3'):
                                        ui.image(coin['image']).classes('w-6 h-6 rounded-full')
                                        with ui.column().classes('gap-0'):
                                            ui.label(coin['name']).classes('font-bold text-slate-700 text-sm')
                                            ui.label(coin['symbol'].upper()).classes('text-xs text-slate-400 font-bold')
                                    ui.label(f"${coin['current_price']:,}").classes('mono font-bold text-slate-700')
                                    
                                    change = coin.get('price_change_percentage_24h', 0) or 0
                                    cls = 'pos-change' if change >= 0 else 'neg-change'
                                    arrow = '▲' if change >= 0 else '▼'
                                    ui.label(f"{arrow} {change:.2f}%").classes(f'mono text-sm {cls}')
                                    
                                    mcap = (coin.get('market_cap', 0) or 0) / 1e9
                                    ui.label(f"${mcap:.2f} B").classes('text-sm text-slate-500 mono')
                                    
                                    vol = (coin.get('total_volume', 0) or 0) / 1e6
                                    ui.label(f"${vol:.0f} M").classes('text-sm text-slate-400 mono')


        # === ТАЙМЕРЫ ===
        def ui_tick():
            nonlocal last_render_ts
            # Обновление арбитража только если есть новые данные и юзер включил сканер
            if state.is_running and backend.GLOBAL_LAST_UPDATE > last_render_ts:
                render_arbitrage()
                last_render_ts = time.time()
            
            # Обновление рынка (если вкладка активна и пуста)
            if tabs.value == tab_market and not market_container.default_slot.children:
                render_market()

        ui.timer(0.5, ui_tick)