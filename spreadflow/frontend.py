from nicegui import ui, app
from fastapi.responses import RedirectResponse
from state import UserState
import backend
import tariffs
import user_profile
import admin_panel
import auth
import subscriptions
import crud
import time
import random
from datetime import datetime, timedelta
from config import DEFAULT_EXCHANGES, DEFAULT_COINS
import market_data 

# === ГЕНЕРАТОР ССЫЛОК ===
def get_trade_link(exchange, symbol):
    try:
        base, quote = symbol.split('/')
        base, quote = base.upper(), quote.upper()
        ex = str(exchange).lower()
        
        if 'binance' in ex: return f"https://www.binance.com/en/trade/{base}_{quote}?type=spot"
        elif 'bybit' in ex: return f"https://www.bybit.com/trade/spot/{base}/{quote}"
        elif 'okx' in ex: return f"https://www.okx.com/trade-spot/{base.lower()}-{quote.lower()}"
        elif 'gate' in ex: return f"https://www.gate.io/trade/{base}_{quote}"
        elif 'kucoin' in ex: return f"https://www.kucoin.com/trade/{base}-{quote}"
        elif 'mexc' in ex: return f"https://www.mexc.com/exchange/{base}_{quote}"
        elif 'htx' in ex: return f"https://www.htx.com/trade/{base.lower()}_{quote.lower()}"
        return "#"
    except:
        return "#"

# === CSS СТИЛИ (GLASSMORPHISM & LAYOUT) ===
def add_custom_styles():
    ui.add_head_html('''
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --glass-bg: rgba(17, 25, 40, 0.75);
                --glass-border: rgba(255, 255, 255, 0.08);
                --neon-purple: #a855f7;
            }
            body {
                font-family: 'Inter', sans-serif;
                background-color: #050505; /* Ultra Dark */
                background-image: radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
                                  radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
                                  radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
                color: #E2E8F0;
            }
            .mono { font-family: 'JetBrains Mono', monospace; }
            
            /* Glass Effect Class */
            .glass {
                background: var(--glass-bg);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid var(--glass-border);
            }
            .glass-hover:hover {
                background: rgba(30, 41, 59, 0.8);
                border-color: rgba(168, 85, 247, 0.4);
                transform: translateY(-2px);
                transition: all 0.3s ease;
            }
            
            .q-drawer { background: rgba(10, 10, 10, 0.95) !important; border-right: 1px solid #222 !important; }
            .q-header { background: rgba(5, 5, 5, 0.8) !important; backdrop-filter: blur(12px); border-bottom: 1px solid #222; }
            
            /* Custom Scrollbar */
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
            
            /* Chart Container */
            .chart-container { min-height: 300px; width: 100%; }
        </style>
    ''')

# === ИНИЦИАЛИЗАЦИЯ UI ===
def init_ui():
    @ui.page('/')
    async def main_page():
        user_info = app.storage.user.get('user_info')
        if not user_info:
            ui.navigate.to('/login')
            return

        add_custom_styles()
        
        # State
        market_search = {'text': ''}
        last_arbitrage_update = 0
        
        # --- HEADER ---
        with ui.header().classes('h-[70px] flex items-center justify-between px-6 z-50'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('bolt', size='32px', color='purple-500').classes('animate-pulse')
                ui.label('SpreadFlow AI').classes('text-xl font-bold tracking-tight text-white')
                ui.label('PRO').classes('text-[10px] bg-purple-500 text-black px-2 py-0.5 rounded font-bold')

            with ui.row().classes('items-center gap-4'):
                with ui.button(on_click=lambda: ui.navigate.to('/profile')).props('flat no-caps'):
                    with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1.5 rounded-full border border-white/10 hover:bg-white/10 transition'):
                        ui.icon('person', size='18px', color='slate-400')
                        ui.label(user_info.get('username', 'Trader')).classes('text-sm font-medium text-slate-200')
                
                ui.button(icon='logout', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')))\
                    .props('flat round dense color=slate-500')

        # --- SIDEBAR & TABS CONTROL ---
        # Мы используем скрытые табы для управления видимостью панелей
        with ui.left_drawer(value=True).classes('w-[260px] py-6 px-4 flex flex-col justify-between z-40'):
            with ui.column().classes('gap-2 w-full'):
                
                # Создаем контроллер вкладок (сами вкладки скрыты, управляем через кнопки)
                tabs = ui.tabs().classes('hidden')
                
                def nav_btn(label, icon, target_tab):
                    # Логика подсветки активной кнопки через binding
                    btn = ui.button(on_click=lambda: tabs.set_value(target_tab))\
                        .classes('w-full text-left justify-start px-4 py-3 rounded-xl transition-all duration-300')\
                        .props('no-caps flat unelevated')
                    
                    with btn:
                        ui.icon(icon, size='20px').classes('mr-3')
                        ui.label(label).classes('font-medium')
                    
                    # Динамическая стилизация
                    def update_style():
                        is_active = tabs.value == target_tab
                        if is_active:
                            btn.classes('bg-purple-600 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]', remove='text-slate-400 hover:text-white hover:bg-white/5')
                        else:
                            btn.classes('text-slate-400 hover:text-white hover:bg-white/5', remove='bg-purple-600 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]')
                    
                    # Подписываемся на изменение табов
                    tabs.on_value_change(update_style)
                    # Инициализируем стиль
                    ui.timer(0.1, update_style, once=True) 
                    return btn

                with tabs:
                    ui.tab('dashboard')
                    ui.tab('market')
                    ui.tab('arbitrage')

                ui.label('MENU').classes('text-xs font-bold text-slate-600 ml-4 mb-2 mt-2')
                nav_btn('Dashboard', 'dashboard', 'dashboard')
                nav_btn('Market Data', 'analytics', 'market')
                nav_btn('Arbitrage Scanner', 'radar', 'arbitrage')
                
                ui.separator().classes('bg-slate-800 my-4')
                ui.label('ACCOUNT').classes('text-xs font-bold text-slate-600 ml-4 mb-2')
                
                ui.button('Profile', icon='settings', on_click=lambda: ui.navigate.to('/profile'))\
                    .classes('w-full text-left justify-start px-4 py-3 rounded-xl text-slate-400 hover:text-white hover:bg-white/5').props('no-caps flat')
                
                ui.button('Subscription', icon='diamond', on_click=lambda: ui.navigate.to('/tariffs'))\
                    .classes('w-full text-left justify-start px-4 py-3 rounded-xl text-amber-400 hover:bg-amber-900/10').props('no-caps flat')

                if user_info.get('role') == 'admin':
                    ui.button('Admin Panel', icon='security', on_click=lambda: ui.navigate.to('/admin'))\
                        .classes('w-full text-left justify-start px-4 py-3 rounded-xl text-red-400 hover:bg-red-900/10').props('no-caps flat')

        # --- CONTENT PANELS ---
        # Используем Tab Panels для переключения контента без "наслоений"
        with ui.column().classes('w-full h-full p-6 bg-transparent'):
            with ui.tab_panels(tabs, value='dashboard').classes('w-full h-full bg-transparent animated fadeIn'):
                
                # === PANEL 1: DASHBOARD ===
                with ui.tab_panel('dashboard').classes('p-0 gap-6'):
                    ui.label('Dashboard Overview').classes('text-2xl font-bold mb-2')
                    
                    # KPI Cards
                    with ui.grid(columns=4).classes('w-full gap-6 mb-6'):
                        def kpi_card(title, val, sub, icon, color_cls):
                            with ui.card().classes('glass p-4 rounded-2xl'):
                                with ui.row().classes('w-full justify-between items-start'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(title).classes('text-slate-500 text-xs font-bold uppercase')
                                        ui.label(val).classes('text-2xl font-bold text-white mono')
                                        ui.label(sub).classes('text-xs text-slate-400')
                                    ui.icon(icon, size='md').classes(color_cls)

                        opps_count = len(backend.GLOBAL_OPPORTUNITIES)
                        max_spr = max([x.get('spread', 0) for x in backend.GLOBAL_OPPORTUNITIES] + [0])
                        
                        kpi_card('Active Opportunities', str(opps_count), 'Updated just now', 'radar', 'text-purple-400')
                        kpi_card('Best Spread', f"{max_spr:.2f}%", 'Global Markets', 'trending_up', 'text-green-400')
                        kpi_card('Market Coins', str(len(market_data.GLOBAL_MARKET_DATA)), 'Tracked Assets', 'token', 'text-blue-400')
                        kpi_card('System Status', 'OPTIMAL', 'Latency: 45ms', 'dns', 'text-emerald-400')

                    # === GRAPH: Spread Distribution (EChart) ===
                    with ui.card().classes('glass w-full p-6 rounded-2xl h-[400px]'):
                        ui.label('Spread Distribution Analysis').classes('text-lg font-bold mb-4')
                        # Генерируем данные для графика
                        spreads = [x.get('spread', 0) for x in backend.GLOBAL_OPPORTUNITIES if x.get('spread', 0) < 20] # Фильтр выбросов
                        
                        # EChart configuration
                        ui.echart({
                            'backgroundColor': 'transparent',
                            'tooltip': {'trigger': 'axis'},
                            'xAxis': {
                                'type': 'category',
                                'data': ['0-1%', '1-2%', '2-3%', '3-5%', '5%+'],
                                'axisLabel': {'color': '#94a3b8'}
                            },
                            'yAxis': {
                                'type': 'value',
                                'splitLine': {'lineStyle': {'color': '#334155', 'type': 'dashed'}},
                                'axisLabel': {'color': '#94a3b8'}
                            },
                            'series': [{
                                'data': [
                                    len([s for s in spreads if 0 <= s < 1]),
                                    len([s for s in spreads if 1 <= s < 2]),
                                    len([s for s in spreads if 2 <= s < 3]),
                                    len([s for s in spreads if 3 <= s < 5]),
                                    len([s for s in spreads if s >= 5])
                                ],
                                'type': 'bar',
                                'itemStyle': {
                                    'color': {'type': 'linear', 'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                            'colorStops': [{'offset': 0, 'color': '#a855f7'}, {'offset': 1, 'color': '#3b82f6'}]}
                                },
                                'barWidth': '40%'
                            }]
                        }).classes('w-full h-full')

                # === PANEL 2: MARKET DATA ===
                with ui.tab_panel('market').classes('p-0'):
                    with ui.row().classes('w-full justify-between items-center mb-6'):
                        ui.label('Market Data').classes('text-2xl font-bold')
                        ui.input(placeholder='Search Asset...', on_change=lambda e: market_search.update({'text': e.value}))\
                            .classes('glass rounded-lg px-3 py-1 w-64').props('dark dense borderless')
                    
                    # Таблица с виртуальным скроллом
                    market_list = ui.column().classes('w-full gap-2')
                    
                    def open_coin_chart(symbol):
                        with ui.dialog() as dialog, ui.card().classes('glass w-[800px] h-[500px] p-0'):
                            with ui.row().classes('w-full p-4 border-b border-white/10 justify-between items-center'):
                                ui.label(f'{symbol} Price Chart').classes('text-xl font-bold')
                                ui.button(icon='close', on_click=dialog.close).props('flat dense round')
                            
                            # Mock Chart Data (так как нет истории в backend)
                            times = [(datetime.now() - timedelta(minutes=i*10)).strftime('%H:%M') for i in range(20)][::-1]
                            base_price = market_data.GLOBAL_MARKET_DATA.get(symbol, {}).get('usd', {}).get('price', 100)
                            prices = [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(20)]
                            
                            ui.echart({
                                'backgroundColor': 'transparent',
                                'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
                                'xAxis': {'type': 'category', 'boundaryGap': False, 'data': times, 'axisLabel': {'color': '#94a3b8'}},
                                'yAxis': {'type': 'value', 'axisLabel': {'color': '#94a3b8'}, 'splitLine': {'lineStyle': {'color': '#334155', 'type': 'dashed'}}},
                                'series': [{'data': prices, 'type': 'line', 'areaStyle': {'opacity': 0.2}, 'smooth': True, 'itemStyle': {'color': '#22c55e'}}]
                            }).classes('w-full h-full p-4')
                        dialog.open()

                    def render_market_list():
                        market_list.clear()
                        search = market_search['text'].lower()
                        # Header
                        with market_list:
                            with ui.row().classes('w-full px-4 py-2 text-slate-500 text-xs font-bold uppercase'):
                                ui.label('Asset').classes('w-1/5')
                                ui.label('Price').classes('w-1/5 text-right')
                                ui.label('24h %').classes('w-1/5 text-right')
                                ui.label('Volume').classes('w-1/5 text-right')
                                ui.label('').classes('w-1/5') # Actions

                            # Scroll Area
                            with ui.scroll_area().classes('w-full h-[65vh] pr-2'):
                                count = 0
                                for sym, data in market_data.GLOBAL_MARKET_DATA.items():
                                    if search and search not in sym.lower(): continue
                                    coin = data.get('usd', {})
                                    if not coin: continue
                                    
                                    price = coin.get('price', 0)
                                    change = coin.get('percent_change_24h', 0)
                                    vol = (coin.get('volume_24h', 0) or 0) / 1e6
                                    
                                    color = 'text-green-400' if change >= 0 else 'text-red-400'
                                    
                                    with ui.row().classes('w-full px-4 py-3 items-center glass-hover rounded-lg cursor-pointer mb-1 border-b border-white/5'):
                                        ui.label(sym).classes('w-1/5 font-bold')
                                        ui.label(f"${price:.2f}" if price > 1 else f"${price:.6f}").classes('w-1/5 text-right mono')
                                        ui.label(f"{change:.2f}%").classes(f'w-1/5 text-right mono {color}')
                                        ui.label(f"${vol:.1f}M").classes('w-1/5 text-right text-slate-500 mono')
                                        with ui.row().classes('w-1/5 justify-end'):
                                            ui.button(icon='show_chart', on_click=lambda s=sym: open_coin_chart(s)).props('flat round dense color=purple')
                                    
                                    count += 1
                                    if count > 50: break # Limit render for performance

                    # Таймер обновления маркета (проверяет, если список пуст)
                    ui.timer(2.0, lambda: render_market_list() if not market_list.default_slot.children and tabs.value == 'market' else None)
                    # При вводе поиска
                    ui.timer(0.5, lambda: render_market_list() if tabs.value == 'market' and len(market_list.default_slot.children) < 2 else None)


                # === PANEL 3: ARBITRAGE SCANNER ===
                with ui.tab_panel('arbitrage').classes('p-0'):
                    with ui.row().classes('w-full justify-between items-center mb-6'):
                        ui.label('Arbitrage Scanner').classes('text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400')
                        with ui.row().classes('gap-2'):
                            ui.chip('Live Data', icon='circle', color='green').props('dense outline')
                            ui.label(f"Updated: {datetime.now().strftime('%H:%M:%S')}").classes('text-xs text-slate-500 mono')

                    scanner_grid = ui.grid(columns=3).classes('w-full gap-4')

                    def render_scanner():
                        scanner_grid.clear()
                        opps = backend.GLOBAL_OPPORTUNITIES
                        opps.sort(key=lambda x: x.get('spread', 0), reverse=True)
                        
                        if not opps:
                            with scanner_grid:
                                ui.label('Scanning markets...').classes('col-span-3 text-center text-slate-500 py-10')
                            return

                        with scanner_grid:
                            for opp in opps[:21]: # Show top 21
                                spread = opp.get('spread', 0)
                                symbol = opp.get('symbol', 'UNK/UNK')
                                
                                # === FIX: БЕЗОПАСНОЕ ПОЛУЧЕНИЕ КЛЮЧЕЙ ===
                                # Проверяем разные варианты ключей, чтобы не было KeyError
                                buy_ex = opp.get('buy_exchange') or opp.get('ask_exchange') or opp.get('buy_venue') or 'Unknown'
                                sell_ex = opp.get('sell_exchange') or opp.get('bid_exchange') or opp.get('sell_venue') or 'Unknown'
                                buy_price = opp.get('buy_price') or opp.get('ask_price') or 0
                                sell_price = opp.get('sell_price') or opp.get('bid_price') or 0

                                border_color = 'border-green-500/30' if spread > 3 else 'border-blue-500/30'
                                glow_class = 'shadow-[0_0_15px_rgba(34,197,94,0.1)]' if spread > 5 else ''

                                with ui.card().classes(f'glass p-0 gap-0 rounded-xl {border_color} {glow_class} group hover:scale-[1.02] transition-transform duration-300'):
                                    # Header
                                    with ui.row().classes('w-full justify-between items-center p-3 bg-white/5 border-b border-white/5'):
                                        ui.label(symbol).classes('font-bold text-white')
                                        ui.label(f"+{spread:.2f}%").classes('text-lg font-black mono text-green-400')
                                    
                                    # Route
                                    with ui.row().classes('w-full p-4 items-center justify-between'):
                                        # Buy Side
                                        with ui.column().classes('items-center gap-1'):
                                            ui.label('BUY').classes('text-[10px] font-bold text-slate-500')
                                            ui.label(str(buy_ex).upper()).classes('text-xs font-bold bg-slate-800 px-2 py-1 rounded text-slate-300')
                                            ui.label(f"{buy_price:.4f}").classes('text-xs mono text-slate-400')
                                        
                                        ui.icon('arrow_right_alt', color='slate-600', size='md')

                                        # Sell Side
                                        with ui.column().classes('items-center gap-1'):
                                            ui.label('SELL').classes('text-[10px] font-bold text-slate-500')
                                            ui.label(str(sell_ex).upper()).classes('text-xs font-bold bg-slate-800 px-2 py-1 rounded text-slate-300')
                                            ui.label(f"{sell_price:.4f}").classes('text-xs mono text-slate-400')

                                    # Actions
                                    with ui.row().classes('w-full px-3 pb-3 gap-2'):
                                        l1 = get_trade_link(buy_ex, symbol)
                                        l2 = get_trade_link(sell_ex, symbol)
                                        ui.button('Buy', on_click=lambda l=l1: ui.open(l)).classes('flex-1 bg-green-900/30 text-green-400 border border-green-500/30 hover:bg-green-500/20').props('dense flat')
                                        ui.button('Sell', on_click=lambda l=l2: ui.open(l)).classes('flex-1 bg-red-900/30 text-red-400 border border-red-500/30 hover:bg-red-500/20').props('dense flat')

                    # Auto-update scanner
                    def auto_refresh_scanner():
                        nonlocal last_arbitrage_update
                        # Обновляем только если вкладка активна И есть новые данные
                        if tabs.value == 'arbitrage' and backend.GLOBAL_LAST_UPDATE > last_arbitrage_update:
                            render_scanner()
                            last_arbitrage_update = time.time()
                        # Если грид пустой (первый рендер), рендерим принудительно
                        elif tabs.value == 'arbitrage' and not scanner_grid.default_slot.children:
                            render_scanner()

                    ui.timer(1.0, auto_refresh_scanner)