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
# === IMPORT UPDATE: Added get_all_plans ===
from crud import get_db, get_all_plans

# === НАЛАШТУВАННЯ БІРЖ ===
# Словник для красивого відображення назв
EXCHANGE_NAMES = {
    'binance': 'Binance',
    'binanceus': 'Binance US',
    'bybit': 'Bybit',
    'okx': 'OKX',
    'gateio': 'Gate.io',
    'gate': 'Gate.io',
    'kucoin': 'KuCoin',
    'mexc': 'MEXC',
    'htx': 'HTX',
    'huobi': 'HTX',
    'bitget': 'Bitget',
    'kraken': 'Kraken',
    'coinbase': 'Coinbase',
    'coinbasepro': 'Coinbase Pro',
    'bingx': 'BingX',
    'poloniex': 'Poloniex'
}

# === ГЕНЕРАТОР ПОСИЛАНЬ ===
def get_trade_link(exchange, symbol):
    """
    Генерує точне пряме посилання на торгову пару для кожної біржі.
    """
    try:
        if not exchange or exchange == 'Unknown': return "#"
        
        # Нормалізація
        base, quote = symbol.split('/')
        base_upper, quote_upper = base.upper(), quote.upper()
        base_lower, quote_lower = base.lower(), quote.lower()
        ex = str(exchange).lower().replace(" ", "").replace(".", "")
        
        # Логіка для кожної біржі
        if 'binance' in ex: 
            return f"https://www.binance.com/en/trade/{base_upper}_{quote_upper}?type=spot"
        
        elif 'bybit' in ex: 
            return f"https://www.bybit.com/trade/spot/{base_upper}/{quote_upper}"
        
        elif 'okx' in ex: 
            return f"https://www.okx.com/trade-spot/{base_lower}-{quote_lower}"
        
        elif 'gate' in ex: 
            return f"https://www.gate.io/trade/{base_upper}_{quote_upper}"
        
        elif 'kucoin' in ex: 
            return f"https://www.kucoin.com/trade/{base_upper}-{quote_upper}"
        
        elif 'mexc' in ex: 
            return f"https://www.mexc.com/exchange/{base_upper}_{quote_upper}"
        
        elif 'htx' in ex or 'huobi' in ex: 
            return f"https://www.htx.com/trade/{base_lower}_{quote_lower}"
            
        elif 'bitget' in ex:
            return f"https://www.bitget.com/spot/{base_upper}{quote_upper}_SPBL"
            
        elif 'bingx' in ex:
            return f"https://bingx.com/en-us/spot/{base_upper}{quote_upper}"
            
        elif 'kraken' in ex:
            return f"https://pro.kraken.com/app/trade/{base_lower}-{quote_lower}"
            
        elif 'coinbase' in ex:
            return f"https://www.coinbase.com/advanced-trade/{base_upper}-{quote_upper}"
            
        elif 'poloniex' in ex:
            return f"https://poloniex.com/trade/{base_upper}_{quote_upper}"

        return "#"
    except Exception as e:
        print(f"Link Gen Error: {e}")
        return "#"

# === CSS СТИЛІ (iOS GLASSMORPHISM) ===
def add_custom_styles():
    ui.add_head_html('''
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            :root {
                /* iOS System Colors (Dark Mode) */
                --glass-bg: rgba(30, 30, 30, 0.60);
                --glass-border: rgba(255, 255, 255, 0.08);
                --ios-blue: #0A84FF;
                --ios-green: #30D158;
                --ios-indigo: #5E5CE6;
                --ios-orange: #FF9F0A;
                --ios-red: #FF453A;
                --ios-gray: #8E8E93;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
                background-color: #000000;
                background-image: 
                    radial-gradient(circle at 15% 50%, rgba(94, 92, 230, 0.15), transparent 25%), 
                    radial-gradient(circle at 85% 30%, rgba(10, 132, 255, 0.15), transparent 25%);
                color: #F5F5F7;
                overflow-x: hidden;
            }
            .mono { font-family: 'JetBrains Mono', 'SF Mono', monospace; }
            
            /* === iOS FROSTED GLASS EFFECT === */
            .glass {
                background: var(--glass-bg);
                backdrop-filter: blur(25px) saturate(180%);
                -webkit-backdrop-filter: blur(25px) saturate(180%);
                border: 1px solid var(--glass-border);
                box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.25);
            }
            
            .glass-hover {
                transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
            }
            
            .glass-hover:hover {
                background: rgba(50, 50, 50, 0.7);
                border-color: rgba(255, 255, 255, 0.2);
                transform: scale(1.01);
                box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.4);
            }
            
            /* Sidebar & Header */
            .q-drawer { 
                background: rgba(18, 18, 18, 0.75) !important; 
                backdrop-filter: blur(35px) saturate(180%) !important;
                -webkit-backdrop-filter: blur(35px) saturate(180%) !important;
                border-right: 1px solid rgba(255,255,255,0.06) !important; 
            }
            
            .q-header { 
                background: rgba(10, 10, 10, 0.65) !important; 
                backdrop-filter: blur(25px) saturate(180%) !important; 
                -webkit-backdrop-filter: blur(25px) saturate(180%) !important;
                border-bottom: 1px solid rgba(255,255,255,0.06); 
            }

            .glass-input {
                background: rgba(118, 118, 128, 0.12) !important;
                backdrop-filter: none !important;
                border: none !important;
                border-radius: 10px !important;
                transition: background 0.3s;
            }
            .glass-input:focus-within {
                background: rgba(118, 118, 128, 0.24) !important;
            }
            
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.4); }

            .text-secondary { color: var(--ios-gray); }
            .tracking-wide { letter-spacing: 0.02em; }
        </style>
    ''')

# === UI INITIALIZATION ===
def init_ui():
    @ui.page('/')
    async def main_page():
        user_info = app.storage.user.get('user_info')
        if not user_info:
            ui.navigate.to('/login')
            return

        current_plan = "FREE"
        current_sub = None
        
        # 1. FETCH SUBSCRIPTION & OVERRIDES
        try:
            db = next(crud.get_db())
            user_db = crud.get_user_by_username(db, user_info.get('username'))
            if user_db:
                # Зберігаємо об'єкт підписки, щоб дістати з нього custom_overrides
                current_sub = crud.get_user_active_sub(db, user_db.id)
                if current_sub: 
                    current_plan = current_sub.plan_name
            db.close()
        except Exception as e:
            print(f"Error fetching plan: {e}")

        add_custom_styles()
        
        # State Variables
        market_search = {'text': ''}
        
        arb_state = {
            'limit': 20,
            'investment': 1000.0,
            'min_spread': 0.1,
            'max_spread': 50.0,
            'min_mcap_m': 0,
            'selected_exchanges': DEFAULT_EXCHANGES,
            'coin_filter': '',
            'last_update': 0
        }
        
        # --- HEADER ---
        with ui.header().classes('h-[70px] flex items-center justify-between px-6 z-50'):
            # Logo Area
            with ui.row().classes('items-center gap-3'):
                with ui.row().classes('items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-b from-[#5E5CE6] to-[#4A48C8] shadow-lg shadow-indigo-500/20 border border-white/10'):
                    ui.icon('bolt', size='20px', color='white')
                
                with ui.column().classes('gap-0'):
                    ui.label('SpreadFlow').classes('text-lg font-bold tracking-wide text-white leading-none')
                    with ui.row().classes('items-center gap-2'):
                         plan_bg = 'bg-[#FF9F0A]/20 text-[#FF9F0A]' if current_plan == 'WHALE' else ('bg-[#5E5CE6]/20 text-[#5E5CE6]' if current_plan == 'PRO' else 'bg-[#8E8E93]/20 text-[#8E8E93]')
                         ui.label(current_plan).classes(f'text-[9px] font-bold px-1.5 py-0.5 rounded-md {plan_bg}')

            # User Menu
            with ui.row().classes('items-center gap-4'):
                with ui.row().classes('hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#1C1C1E]/60 border border-white/5 backdrop-blur-md'):
                    ui.icon('account_balance_wallet', size='14px', color='#8E8E93')
                    ui.label('$ 0.00').classes('text-xs font-medium text-white mono')

                with ui.button(on_click=lambda: ui.navigate.to('/profile')).props('flat no-caps dense'):
                    with ui.row().classes('items-center gap-2.5'):
                        ui.avatar(icon='person', color='grey-9', text_color='grey-4').classes('border border-white/10 w-8 h-8 text-sm')
                        with ui.column().classes('gap-0 text-left'):
                            ui.label(user_info.get('username', 'Trader')).classes('text-xs font-semibold text-white')
                            ui.label('Online').classes('text-[9px] text-[#30D158]')
                
                ui.button(icon='logout', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')))\
                    .props('flat round dense color=grey-6').tooltip('Logout')

        # --- SIDEBAR & CONTENT ---
        with ui.left_drawer(value=True).classes('w-[240px] py-6 px-3 flex flex-col justify-between z-40'):
            with ui.column().classes('gap-1.5 w-full'):
                tabs = ui.tabs().classes('hidden')
                
                def nav_btn(label, icon, target_tab):
                    btn = ui.button(on_click=lambda: tabs.set_value(target_tab))\
                        .classes('w-full text-left justify-start px-3 py-2.5 rounded-xl transition-all duration-300')\
                        .props('no-caps flat unelevated')
                    with btn:
                        ui.icon(icon, size='18px').classes('mr-3')
                        ui.label(label).classes('text-sm font-medium')
                    
                    def update_style():
                        is_active = tabs.value == target_tab
                        if is_active:
                            btn.classes('bg-[#0A84FF]/15 text-[#0A84FF]', remove='text-[#8E8E93] hover:text-white hover:bg-white/5')
                        else:
                            btn.classes('text-[#8E8E93] hover:text-white hover:bg-white/5', remove='bg-[#0A84FF]/15 text-[#0A84FF]')
                    
                    tabs.on_value_change(update_style)
                    ui.timer(0.1, update_style, once=True) 
                    return btn

                with tabs:
                    ui.tab('dashboard')
                    ui.tab('market')
                    ui.tab('arbitrage')

                ui.label('PLATFORM').classes('text-[10px] font-bold text-[#8E8E93] ml-3 mb-1 mt-2 tracking-widest opacity-60')
                nav_btn('Dashboard', 'dashboard', 'dashboard')
                nav_btn('Arbitrage Scanner', 'radar', 'arbitrage')
                nav_btn('Market Data', 'analytics', 'market')
                
                ui.separator().classes('bg-white/5 my-4 mx-2')
                ui.label('ACCOUNT').classes('text-[10px] font-bold text-[#8E8E93] ml-3 mb-1 tracking-widest opacity-60')
                
                nav_btn('Statistics', 'insights', 'dashboard') 
                
                ui.button('Upgrade Plan', icon='diamond', on_click=lambda: ui.navigate.to('/tariffs'))\
                    .classes('w-full text-left justify-start px-3 py-2.5 rounded-xl text-[#FF9F0A] bg-[#FF9F0A]/10 hover:bg-[#FF9F0A]/20 mt-2').props('no-caps flat')

                if user_info.get('role') == 'admin':
                    ui.button('Admin Panel', icon='security', on_click=lambda: ui.navigate.to('/admin'))\
                        .classes('w-full text-left justify-start px-3 py-2.5 rounded-xl text-[#FF453A] hover:bg-[#FF453A]/10').props('no-caps flat')

        # --- CONTENT AREA ---
        with ui.column().classes('w-full h-full p-6 lg:p-8 bg-transparent scroll-smooth'):
            with ui.tab_panels(tabs, value='dashboard').classes('w-full h-full bg-transparent animated fadeIn'):
                
                # === PANEL 1: DASHBOARD ===
                with ui.tab_panel('dashboard').classes('p-0 gap-8'):
                    with ui.row().classes('justify-between items-end'):
                        with ui.column().classes('gap-1'):
                            ui.label(f"Good evening, {user_info.get('username')}").classes('text-3xl font-bold text-white tracking-tight')
                            ui.label('Overview of your crypto opportunities').classes('text-[#8E8E93] text-sm')
                        
                        ui.chip(f'{datetime.now().strftime("%d %b")}', icon='calendar_today', color='grey-9').props('outline square dense').classes('text-[#8E8E93]')

                    # KPI Cards
                    with ui.grid(columns=4).classes('w-full gap-5'):
                        def kpi_card(title, val, sub, icon, color_hex, grad_from):
                            with ui.card().classes(f'glass p-5 rounded-[20px] relative overflow-hidden group hover:-translate-y-1 glass-hover'):
                                ui.element('div').classes(f'absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-[{grad_from}] to-transparent opacity-10 blur-3xl rounded-full')
                                
                                with ui.column().classes('gap-3 z-10 relative'):
                                    with ui.row().classes('w-full justify-between items-start'):
                                        with ui.element('div').classes(f'p-2 rounded-xl bg-[{color_hex}]/15'):
                                            ui.icon(icon, size='20px', color=color_hex)
                                        ui.icon('arrow_outward', size='16px', color='#8E8E93').classes('opacity-50')

                                    with ui.column().classes('gap-0.5'):
                                        ui.label(val).classes('text-2xl font-bold text-white mono tracking-tight')
                                        ui.label(title).classes('text-[#8E8E93] text-xs font-medium')
                                    
                                    ui.label(sub).classes(f'text-[10px] text-[{color_hex}] font-medium opacity-80')

                        opps_count = len(backend.GLOBAL_OPPORTUNITIES)
                        max_spr = max([x.get('spread', 0) for x in backend.GLOBAL_OPPORTUNITIES] + [0])
                        market_coins_count = len(getattr(market_data, 'GLOBAL_MARKET_DATA', {}))
                        
                        kpi_card('Opportunities', str(opps_count), 'Live Updates', 'radar', '#5E5CE6', '#5E5CE6')
                        kpi_card('Best Spread', f"{max_spr:.2f}%", 'Global Peak', 'trending_up', '#30D158', '#30D158')
                        kpi_card('Assets Tracked', str(market_coins_count), 'Market Depth', 'token', '#0A84FF', '#0A84FF')
                        kpi_card('System Status', 'Active', 'Uptime 99%', 'dns', '#FF9F0A', '#FF9F0A')

                    # Distribution Graph
                    with ui.card().classes('glass w-full p-6 rounded-[24px] h-[380px]'):
                        with ui.row().classes('justify-between w-full mb-6 items-center'):
                            ui.label('Spread Distribution').classes('text-lg font-semibold text-white')
                            with ui.button(icon='refresh', on_click=lambda: None).props('flat dense round color=grey-6'):
                                pass

                        spreads = [x.get('spread', 0) for x in backend.GLOBAL_OPPORTUNITIES if x.get('spread', 0) < 20]
                        
                        ui.echart({
                            'backgroundColor': 'transparent',
                            'tooltip': {'trigger': 'axis', 'backgroundColor': 'rgba(20,20,20,0.8)', 'borderColor': 'rgba(255,255,255,0.1)', 'textStyle': {'color': '#fff'}, 'borderRadius': 8},
                            'grid': {'left': '2%', 'right': '2%', 'bottom': '2%', 'top': '10%', 'containLabel': True},
                            'xAxis': {
                                'type': 'category',
                                'data': ['0-1%', '1-2%', '2-3%', '3-5%', '5%+'],
                                'axisLine': {'show': False},
                                'axisTick': {'show': False},
                                'axisLabel': {'color': '#8E8E93', 'fontSize': 11}
                            },
                            'yAxis': {
                                'type': 'value',
                                'splitLine': {'lineStyle': {'color': 'rgba(255,255,255,0.05)', 'type': 'solid'}},
                                'axisLabel': {'color': '#8E8E93', 'fontSize': 11}
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
                                            'colorStops': [{'offset': 0, 'color': '#5E5CE6'}, {'offset': 1, 'color': '#0A84FF'}]},
                                    'borderRadius': [6, 6, 6, 6]
                                },
                                'barWidth': '32px'
                            }]
                        }).classes('w-full h-full')

                # === PANEL 2: MARKET DATA ===
                with ui.tab_panel('market').classes('p-0'):
                    with ui.row().classes('w-full justify-between items-center mb-6'):
                        ui.label('Market').classes('text-3xl font-bold tracking-tight')
                        ui.input(
                            placeholder='Search', 
                            on_change=lambda e: (market_search.update({'text': e.value}), render_market_list())
                        ).classes('glass-input w-72 px-3 py-1 text-sm').props('dark borderless dense prepend-icon=search debounce=300 input-class="text-white"')
                    
                    market_list = ui.column().classes('w-full gap-2')
                    
                    def open_coin_chart(symbol):
                        with ui.dialog() as dialog, ui.card().classes('glass w-[800px] h-[500px] p-0 rounded-[24px]'):
                            with ui.row().classes('w-full p-4 border-b border-white/5 justify-between items-center bg-black/20'):
                                ui.label(f'{symbol}').classes('text-lg font-bold')
                                ui.button(icon='close', on_click=dialog.close).props('flat dense round color=grey-6')
                            
                            times = [(datetime.now() - timedelta(minutes=i*10)).strftime('%H:%M') for i in range(20)][::-1]
                            coin_data = market_data.GLOBAL_MARKET_DATA.get(symbol, {})
                            base_price = coin_data.get('price') or 100
                            if 'usd' in coin_data and not coin_data.get('price'): 
                                base_price = coin_data.get('usd', {}).get('price') or 100

                            prices = [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(20)]
                            
                            ui.echart({
                                'backgroundColor': 'transparent',
                                'grid': {'left': '3%', 'right': '4%', 'bottom': '5%', 'top': '5%', 'containLabel': True},
                                'xAxis': {'type': 'category', 'boundaryGap': False, 'data': times, 'axisLabel': {'color': '#8E8E93'}},
                                'yAxis': {'type': 'value', 'axisLabel': {'color': '#8E8E93'}, 'splitLine': {'lineStyle': {'color': 'rgba(255,255,255,0.05)'}}},
                                'series': [{'data': prices, 'type': 'line', 'areaStyle': {'opacity': 0.15, 'color': '#30D158'}, 'smooth': True, 'itemStyle': {'color': '#30D158'}, 'showSymbol': False, 'lineStyle': {'width': 2}}]
                            }).classes('w-full h-full p-4')
                        dialog.open()

                    def render_market_list():
                        market_list.clear()
                        search = market_search['text'].lower()
                        with market_list:
                            with ui.row().classes('sticky top-0 z-20 w-full px-6 py-3 text-[#8E8E93] text-[10px] font-bold uppercase tracking-wider bg-[#1c1c1e]/80 backdrop-blur-md rounded-xl mb-2'):
                                ui.label('Token').classes('w-1/5')
                                ui.label('Price').classes('w-1/5 text-right')
                                ui.label('24h').classes('w-1/5 text-right')
                                ui.label('Volume').classes('w-1/5 text-right')
                                ui.label('Analytics').classes('w-1/5 text-right pr-2')

                            with ui.scroll_area().classes('w-full h-[65vh] pr-2'):
                                count = 0
                                data_source = getattr(market_data, 'GLOBAL_MARKET_DATA', {})
                                for sym, data in data_source.items():
                                    if search and search not in sym.lower(): continue
                                    
                                    price = data.get('price') or 0
                                    change = data.get('price_change_24h') or 0
                                    vol = (data.get('total_volume') or 0) / 1e6
                                    image_url = data.get('image')
                                    
                                    if 'usd' in data: 
                                        coin = data.get('usd', {})
                                        price = coin.get('price') or 0
                                        change = coin.get('percent_change_24h') or 0
                                        vol = (coin.get('volume_24h') or 0) / 1e6
                                        if not image_url: image_url = coin.get('image')

                                    color = 'text-[#30D158]' if change >= 0 else 'text-[#FF453A]'
                                    bg_color = 'bg-[#30D158]/10' if change >= 0 else 'bg-[#FF453A]/10'
                                    
                                    with ui.row().classes('w-full px-6 py-4 items-center glass-hover rounded-xl cursor-pointer mb-2 group border border-transparent hover:border-white/5'):
                                        with ui.row().classes('w-1/5 items-center gap-3'):
                                            if image_url:
                                                ui.image(image_url).classes('w-8 h-8 rounded-full bg-white/10')
                                            else:
                                                ui.avatar(sym[0], color='grey-9', text_color='white').classes('text-xs font-bold w-8 h-8')
                                            
                                            with ui.column().classes('gap-0'):
                                                ui.label(sym.split('/')[0]).classes('font-bold text-white text-sm')
                                                ui.label('Coin').classes('text-[10px] text-[#8E8E93]')
                                        
                                        ui.label(f"${price:,.2f}" if price > 1 else f"${price:.6f}").classes('w-1/5 text-right mono text-white text-sm')
                                        
                                        with ui.row().classes(f'w-1/5 justify-end items-center'):
                                            ui.label(f"{change:+.2f}%").classes(f'text-xs font-bold px-2 py-1 rounded-lg {color} {bg_color}')
                                            
                                        ui.label(f"${vol:,.1f}M").classes('w-1/5 text-right text-[#8E8E93] text-sm mono')
                                        
                                        with ui.row().classes('w-1/5 justify-end'):
                                            ui.button(icon='bar_chart', on_click=lambda s=sym: open_coin_chart(s))\
                                                .props('flat round dense color=grey-6').classes('opacity-0 group-hover:opacity-100 transition-opacity')
                                    
                                    count += 1
                                    if count > 50: break

                    ui.timer(2.0, lambda: render_market_list() if not market_list.default_slot.children and tabs.value == 'market' else None)

                # === PANEL 3: ARBITRAGE SCANNER (UPDATED) ===
                with ui.tab_panel('arbitrage').classes('p-0'):
                    
                    # --- FILTERS & CONTROLS ---
                    with ui.card().classes('glass w-full p-6 rounded-[24px] mb-8'):
                        with ui.row().classes('w-full items-center justify-between mb-6'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('tune', color='white', size='20px')
                                ui.label('Scanner Config').classes('text-lg font-bold text-white')
                            
                            with ui.row().classes('items-center gap-4'):
                                total_raw = len(backend.GLOBAL_OPPORTUNITIES)
                                ui.label(f"Raw Items: {total_raw}").classes('text-xs font-mono text-[#8E8E93] bg-white/5 px-2 py-1 rounded')
                                ui.button(icon='refresh', on_click=lambda: render_scanner()).props('flat dense round color=indigo-4')

                        with ui.grid(columns=4).classes('w-full gap-6 items-start'):
                            
                            with ui.column().classes('w-full gap-2'):
                                ui.label('INVESTMENT ($)').classes('text-[10px] font-bold text-[#8E8E93] tracking-wider')
                                ui.number(value=arb_state['investment'], format='%.2f', 
                                    on_change=lambda e: (arb_state.update({'investment': e.value}), render_scanner())
                                ).classes('glass-input w-full px-3 py-1').props('dark borderless input-class="text-[#30D158] font-bold mono"')
                            
                            with ui.column().classes('w-full gap-2'):
                                ui.label('SPREAD RANGE (%)').classes('text-[10px] font-bold text-[#8E8E93] tracking-wider')
                                with ui.row().classes('gap-2 w-full'):
                                    ui.number(value=arb_state['min_spread'], step=0.1, min=0,
                                        on_change=lambda e: (arb_state.update({'min_spread': e.value}), render_scanner())
                                    ).classes('glass-input w-1/2 px-2').props('dark borderless dense suffix="Min"')
                                    
                                    ui.number(value=arb_state['max_spread'], step=0.1, max=100,
                                        on_change=lambda e: (arb_state.update({'max_spread': e.value}), render_scanner())
                                    ).classes('glass-input w-1/2 px-2').props('dark borderless dense suffix="Max"')

                            with ui.column().classes('w-full gap-2'):
                                ui.label('MIN CAP ($M)').classes('text-[10px] font-bold text-[#8E8E93] tracking-wider')
                                ui.number(value=arb_state['min_mcap_m'], min=0, step=10,
                                    on_change=lambda e: (arb_state.update({'min_mcap_m': e.value}), render_scanner())
                                ).classes('glass-input w-full px-3').props('dark borderless dense')

                            with ui.column().classes('w-full gap-2'):
                                ui.label('LIMIT').classes('text-[10px] font-bold text-[#8E8E93] tracking-wider')
                                ui.select(options=[20, 40, 60, 100], value=arb_state['limit'],
                                    on_change=lambda e: (arb_state.update({'limit': e.value}), render_scanner())
                                ).classes('glass-input w-full px-3').props('dark borderless dense options-dense behavior="menu"')

                        with ui.expansion('Advanced Filters', icon='layers').classes('w-full mt-4 text-[#8E8E93] text-sm'):
                            with ui.grid(columns=2).classes('w-full gap-6 mt-3'):
                                ui.select(options=DEFAULT_EXCHANGES, multiple=True, value=arb_state['selected_exchanges'], label='Exchanges',
                                    on_change=lambda e: (arb_state.update({'selected_exchanges': e.value}), render_scanner())
                                ).classes('glass-input w-full px-3').props('dark borderless use-chips dense')
                                
                                ui.input(placeholder='Filter Coins (BTC, ETH...)', 
                                    on_change=lambda e: (arb_state.update({'coin_filter': e.value}), render_scanner())
                                ).classes('glass-input w-full px-3').props('dark borderless dense prepend-icon=search debounce=500')

                    # --- SCANNER GRID ---
                    scanner_grid = ui.grid(columns=3).classes('w-full gap-5')

                    def render_scanner():
                        scanner_grid.clear()
                        opps = backend.GLOBAL_OPPORTUNITIES
                        
                        # === 1. ВСТАНОВЛЕННЯ ЛІМІТІВ (ДИНАМІЧНО З БД) ===
                        # Default fallback
                        active_rules = {'max_spread': 1.0, 'limit': 5}
                        
                        # Fetch plans from DB to find current user's limits
                        db_plans = []
                        try:
                            # Оптимізація: в реальному проекті це краще кешувати
                            db = next(get_db())
                            db_plans = get_all_plans(db)
                            db.close()
                        except:
                            pass

                        # Convert DB plans to dictionary for lookup
                        plan_map = {}
                        for p in db_plans:
                            # Assuming Plan model has max_spread and max_listings
                            # If not, use defaults
                            m_spread = getattr(p, 'max_spread', 1.0)
                            m_limit = getattr(p, 'active_deals_limit', 5) # Check model field name
                            plan_map[p.name] = {'max_spread': float(m_spread), 'limit': int(m_limit)}
                        
                        # Add hardcoded fallback if DB is empty
                        if not plan_map:
                            plan_map = {
                                'FREE': {'max_spread': 1.0, 'limit': 5},
                                'START': {'max_spread': 3.0, 'limit': 20},
                                'PRO': {'max_spread': 10.0, 'limit': 100},
                                'WHALE': {'max_spread': 1000.0, 'limit': 1000}
                            }

                        user_role = user_info.get('role', 'user')
                        
                        # Determine active rules
                        if user_role == 'admin':
                            active_rules = {'max_spread': 1000.0, 'limit': 1000}
                        else:
                            active_rules = plan_map.get(current_plan, plan_map.get('FREE', active_rules))

                        # 1.3 АДМІН ОВЕРРАЙДИ (Override) - Найвищий пріоритет
                        overrides = current_sub.custom_overrides if current_sub and current_sub.custom_overrides else {}
                        
                        system_max_spread = float(overrides.get('max_spread', active_rules['max_spread']))
                        system_card_limit = int(overrides.get('limit', active_rules['limit']))

                        # 2. ФІЛЬТРАЦІЯ (User Filters)
                        filtered_opps = []
                        
                        # Особисті фільтри з UI (state)
                        ui_inv = arb_state['investment'] or 0
                        ui_min_s = arb_state['min_spread'] or 0
                        ui_max_s = arb_state['max_spread'] or 100
                        ui_min_cap = (arb_state['min_mcap_m'] or 0) * 1e6
                        ui_sel_exs = set(arb_state['selected_exchanges'])
                        ui_filter_coin = arb_state['coin_filter'].upper()
                        
                        m_data = getattr(market_data, 'GLOBAL_MARKET_DATA', {})

                        for opp in opps:
                            spread = opp.get('spread', 0)
                            sym = opp.get('symbol', '')
                            
                            # 2.1 Перевірка СИСТЕМНОГО ліміту (Тариф/Адмін)
                            if spread > system_max_spread: continue
                            
                            # 2.2 Перевірка КОРИСТУВАЦЬКОГО фільтру
                            if not (ui_min_s <= spread <= ui_max_s): continue
                            
                            # === Обробка назв бірж ===
                            b_ex_raw = (opp.get('buy_exchange') or opp.get('buy_ex') or opp.get('exchange_buy') or 
                                      opp.get('ask_exchange') or opp.get('buy_venue') or opp.get('ex_buy') or 'Unknown')
                            s_ex_raw = (opp.get('sell_exchange') or opp.get('sell_ex') or opp.get('exchange_sell') or
                                      opp.get('bid_exchange') or opp.get('sell_venue') or opp.get('ex_sell') or 'Unknown')
                            
                            b_ex_lower = str(b_ex_raw).lower()
                            s_ex_lower = str(s_ex_raw).lower()
                            
                            # Фільтр по біржах (якщо вибрані користувачем)
                            if ui_sel_exs:
                                b_match = (b_ex_lower == 'unknown') or any(sel in b_ex_lower for sel in ui_sel_exs)
                                s_match = (s_ex_lower == 'unknown') or any(sel in s_ex_lower for sel in ui_sel_exs)
                                if not (b_match and s_match): continue

                            # Фільтр по монеті
                            if ui_filter_coin and ui_filter_coin not in sym: continue
                            
                            # Фільтр по капіталізації
                            mcap_val = 0
                            coin_data = m_data.get(sym)
                            if coin_data:
                                mcap_val = coin_data.get('market_cap', 0) or 0
                                if not mcap_val and 'usd' in coin_data:
                                    mcap_val = coin_data['usd'].get('market_cap', 0) or 0
                            
                            if ui_min_cap > 0 and mcap_val < ui_min_cap: continue

                            # Зберігаємо додаткові дані для відображення
                            opp['_display_buy_ex'] = b_ex_raw
                            opp['_display_sell_ex'] = s_ex_raw
                            opp['_mcap'] = mcap_val
                            filtered_opps.append(opp)

                        # Сортування
                        filtered_opps.sort(key=lambda x: x.get('spread', 0), reverse=True)
                        
                        # 3. ВІДОБРАЖЕННЯ (View Limit)
                        ui_limit = arb_state['limit']
                        final_view_limit = min(ui_limit, system_card_limit)
                        
                        # Якщо користувач обмежений тарифом
                        is_restricted = len(filtered_opps) > final_view_limit and user_role != 'admin'
                        
                        visible_opps = filtered_opps[:final_view_limit]
                        
                        with scanner_grid:
                            # === UPSELL CARD (FIRST) ===
                            if is_restricted:
                                with ui.card().classes('glass p-6 gap-4 rounded-2xl border-dashed border-[#FF9F0A]/30 items-center justify-center opacity-90 hover:opacity-100 transition-opacity bg-[#FF9F0A]/5'):
                                    ui.icon('lock', size='40px', color='#FF9F0A')
                                    with ui.column().classes('items-center gap-1 text-center'):
                                        hidden_count = len(filtered_opps) - final_view_limit
                                        ui.label(f'+{hidden_count} Premium Spreads').classes('text-lg font-bold text-white')
                                        ui.label(f'Your {current_plan} plan limits visibility').classes('text-xs text-[#8E8E93]')
                                    ui.button('Unlock Full Access', on_click=lambda: ui.navigate.to('/tariffs')).classes('bg-[#FF9F0A] text-black hover:bg-[#FF9F0A]/80 rounded-xl px-6 w-full').props('no-caps')

                            if not visible_opps and not is_restricted:
                                with ui.column().classes('col-span-3 items-center justify-center py-24 opacity-60'):
                                    ui.icon('search', size='64px', color='#8E8E93')
                                    ui.label(f'No results found (Raw: {len(opps)} items)').classes('text-[#8E8E93] text-lg font-medium mt-4')
                                    if len(opps) > 0:
                                        ui.label('Try relaxing filters').classes('text-sm text-[#FF453A]')
                            
                            for opp in visible_opps:
                                spread = opp.get('spread', 0)
                                symbol = opp.get('symbol', 'UNK/UNK')
                                
                                b_id = opp.get('_display_buy_ex', 'Unknown')
                                s_id = opp.get('_display_sell_ex', 'Unknown')
                                
                                b_name = EXCHANGE_NAMES.get(b_id.lower(), b_id.upper())
                                s_name = EXCHANGE_NAMES.get(s_id.lower(), s_id.upper())

                                buy_price = opp.get('buy_price', 0) or opp.get('ask_price', 0)
                                sell_price = opp.get('sell_price', 0) or opp.get('bid_price', 0)

                                profit = ui_inv * (spread / 100)
                                
                                mcap_val = opp.get('_mcap', 0)
                                mcap_str = f"MCAP: ${mcap_val/1e6:.1f}M" if mcap_val > 0 else "MCAP: N/A"

                                border_col = 'border-[#30D158]/30' if spread > 3 else 'border-[#0A84FF]/30'
                                glow = 'shadow-[0_0_20px_rgba(48,209,88,0.15)]' if spread > 5 else ''
                                spread_color = 'text-[#30D158]' if spread > 1 else 'text-[#0A84FF]'

                                with ui.card().classes(f'glass p-0 gap-0 rounded-2xl {border_col} {glow} group hover:scale-[1.02] glass-hover'):
                                    with ui.row().classes('w-full justify-between items-center p-4 bg-white/5 border-b border-white/5'):
                                        with ui.row().classes('items-center gap-3'):
                                            ui.avatar(symbol[0], color='grey-9', text_color='white', size='sm').classes('text-xs font-bold')
                                            with ui.column().classes('gap-0'):
                                                ui.label(symbol).classes('font-bold text-white tracking-wide')
                                                ui.label(mcap_str).classes('text-[9px] text-[#8E8E93] font-mono')
                                        
                                        ui.label(f"+{spread:.2f}%").classes(f'text-xl font-black mono {spread_color}')
                                    
                                    with ui.row().classes('w-full p-5 items-center justify-between'):
                                        with ui.column().classes('items-start gap-1'):
                                            ui.label(b_name).classes('text-[9px] font-bold bg-[#1C1C1E] px-2 py-1 rounded text-[#0A84FF] tracking-wider')
                                            ui.label(f"${buy_price:.4f}").classes('text-sm mono text-white')
                                        
                                        with ui.column().classes('items-center gap-1'):
                                            ui.icon('arrow_forward', color='#8E8E93', size='16px')
                                            ui.label(f'+${profit:.2f}').classes('text-[10px] font-bold text-[#30D158] bg-[#30D158]/10 px-2 py-0.5 rounded-full')

                                        with ui.column().classes('items-end gap-1'):
                                            ui.label(s_name).classes('text-[9px] font-bold bg-[#1C1C1E] px-2 py-1 rounded text-[#FF453A] tracking-wider')
                                            ui.label(f"${sell_price:.4f}").classes('text-sm mono text-white')

                                    with ui.row().classes('w-full px-4 pb-4 gap-3'):
                                        l1 = get_trade_link(b_id, symbol)
                                        l2 = get_trade_link(s_id, symbol)
                                        
                                        btn1 = ui.button('Buy', on_click=lambda l=l1: ui.navigate.to(l, new_tab=True)).classes('flex-1 bg-[#0A84FF]/15 text-[#0A84FF] hover:bg-[#0A84FF]/30 rounded-xl').props('dense flat no-caps')
                                        if l1 == "#": btn1.disable()
                                            
                                        btn2 = ui.button('Sell', on_click=lambda l=l2: ui.navigate.to(l, new_tab=True)).classes('flex-1 bg-[#FF453A]/15 text-[#FF453A] hover:bg-[#FF453A]/30 rounded-xl').props('dense flat no-caps')
                                        if l2 == "#": btn2.disable()

                    def auto_refresh_scanner():
                        nonlocal arb_state
                        if tabs.value == 'arbitrage' and backend.GLOBAL_LAST_UPDATE > arb_state['last_update']:
                            render_scanner()
                            arb_state['last_update'] = time.time()
                        elif tabs.value == 'arbitrage' and not scanner_grid.default_slot.children:
                            render_scanner()

                    ui.timer(1.0, auto_refresh_scanner)