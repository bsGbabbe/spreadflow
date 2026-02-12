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
import market_data 

# === ГЕНЕРАТОР ССЫЛОК ===
def get_trade_link(exchange, symbol):
    """
    Генерирует максимально точную ссылку на торговую пару.
    """
    try:
        # Разделяем BASE/QUOTE (например, BTC/USDT)
        base, quote = symbol.split('/')
        base = base.upper()
        quote = quote.upper()
        ex = exchange.lower()
        
        # --- BINANCE ---
        if ex == 'binance':
            # Стандартная ссылка Binance Spot: BTC_USDT
            return f"https://www.binance.com/en/trade/{base}_{quote}?type=spot"
            
        # --- BYBIT ---
        elif ex == 'bybit':
            # Bybit Spot: BTC/USDT
            return f"https://www.bybit.com/trade/spot/{base}/{quote}"
            
        # --- OKX ---
        elif ex == 'okx':
            # OKX Spot: BTC-USDT
            return f"https://www.okx.com/trade-spot/{base.lower()}-{quote.lower()}"
            
        # --- GATE.IO ---
        elif ex == 'gateio':
            # Gate: BTC_USDT
            return f"https://www.gate.io/trade/{base}_{quote}"
            
        # --- KUCOIN ---
        elif ex == 'kucoin':
            # KuCoin: BTC-USDT
            return f"https://www.kucoin.com/trade/{base}-{quote}"
            
        # --- MEXC ---
        elif ex == 'mexc':
            # MEXC: BTC_USDT
            return f"https://www.mexc.com/exchange/{base}_{quote}"
            
        # --- HTX (Huobi) ---
        elif ex == 'htx':
            # HTX: btc_usdt (маленькими)
            return f"https://www.htx.com/trade/{base.lower()}_{quote.lower()}"
            
        # --- BITGET ---
        elif ex == 'bitget':
            # Bitget: BTCUSDT (слитно)
            return f"https://www.bitget.com/spot/{base}{quote}"
            
        # --- KRAKEN ---
        elif ex == 'kraken':
            # Kraken Pro: BTC-USDT
            return f"https://pro.kraken.com/app/trade/{base}-{quote}"
            
        # --- COINBASE ---
        elif ex == 'coinbase':
            # Coinbase Advanced: BTC-USDT
            return f"https://www.coinbase.com/advanced-trade/spot/{base}-{quote}"
            
        # --- BINGX ---
        elif ex == 'bingx':
            # BingX: BTC-USDT
            return f"https://bingx.com/en-us/spot/{base}-{quote}"
            
        # --- POLONIEX ---
        elif ex == 'poloniex':
            # Poloniex: BTC_USDT
            return f"https://poloniex.com/spot/{base}_{quote}"
            
        else:
            # Универсальный поиск, если биржа неизвестна
            return f"https://www.google.com/search?q={exchange}+spot+{base}+{quote}"
    except:
        return "#"


def init_ui():
    @ui.page('/')
    def main_page():
        user = auth.get_current_user()
        if not user: return RedirectResponse('/login')

        state = UserState()
        last_render_ts = 0
        calc_state = {'amount': 1000.0, 'spread': 1.5, 'fee_buy': 0.1, 'fee_sell': 0.1, 'cycles': 1}
        
        # Состояние поиска для вкладки Market
        market_search = {'text': ''}

        # === СТИЛИ ===
        ui.add_head_html('''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap');
            body { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
            .mono { font-family: 'Roboto Mono', monospace; }
            
            .q-table__top, .q-table__bottom, thead tr:first-child th {
                background-color: #f8fafc; font-weight: bold; color: #64748b;
            }
            .q-table tbody td { font-size: 13px; font-weight: 600; color: #334155; }
            
            .ex-badge { 
                cursor: pointer; transition: transform 0.2s; text-decoration: none; 
                display: inline-flex; align-items: center; justify-content: center;
                padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;
            }
            .ex-badge:hover { transform: scale(1.1); opacity: 0.8; }
            .badge-gray { background: #f1f5f9; color: #0f172a; border: 1px solid #e2e8f0; }
            .badge-green { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
            
            .pos-change { color: #16a34a; }
            .neg-change { color: #dc2626; }
        </style>
        ''')

        # === SIDEBAR ===
        with ui.left_drawer(value=True).classes('bg-white border-r border-gray-200 p-6 flex flex-col gap-6 shadow-sm'):
            ui.label("SPREADFLOW").classes('text-2xl font-black text-slate-800 tracking-tighter')
            
            with ui.row().classes('items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100'):
                ui.avatar('person', color='slate-300', text_color='white').classes('shadow-sm')
                with ui.column().classes('gap-0'):
                    ui.label(user.username).classes('font-bold text-slate-700 text-sm')
                    ui.label(user.role).classes('text-xs text-slate-400 uppercase font-bold')

            ui.separator().classes('bg-slate-100')
            
            with ui.row().classes('items-center gap-2 px-2'):
                ui.spinner('dots', size='sm', color='green')
                coins_count_label = ui.label("Scanner Active").classes('text-xs font-bold text-green-600')

            with ui.column().classes('w-full gap-2'):
                ui.button('Profile', icon='settings', on_click=lambda: ui.navigate.to('/profile')).props('flat align=left color=slate').classes('w-full')
                ui.button('Subscriptions', icon='diamond', on_click=lambda: subscriptions.show_subs_dialog(user)).props('flat align=left color=slate').classes('w-full')
                if user.role == 'admin':
                    ui.button('Admin Panel', icon='admin_panel_settings', on_click=lambda: ui.navigate.to('/admin')).props('flat align=left color=red').classes('w-full')
                ui.button('Logout', icon='logout', on_click=lambda: auth.logout()).props('flat align=left color=slate').classes('w-full')

        # === MAIN ===
        with ui.column().classes('w-full p-6 max-w-7xl mx-auto gap-6'):
            
            with ui.tabs().classes('w-full text-slate-600') as tabs:
                tab_arb = ui.tab('ARBITRAGE', icon='bolt')
                tab_market = ui.tab('MARKET OVERVIEW', icon='bar_chart')
            
            with ui.tab_panels(tabs, value=tab_arb).classes('w-full bg-transparent'):
                
                # --- Вкладка 1: АРБИТРАЖ ---
                with ui.tab_panel(tab_arb).classes('p-0 gap-4'):
                    
                    # --- ФИЛЬТРЫ ---
                    with ui.expansion('⚙️ Filters & Investment', icon='tune').classes('w-full bg-white rounded-xl shadow-sm border border-slate-200 mb-4'):
                        with ui.column().classes('p-4 w-full'):
                            with ui.row().classes('w-full gap-6 mb-4'):
                                with ui.column().classes('flex-1'):
                                    ui.label("Invest ($)").classes('text-xs font-bold text-slate-400')
                                    ui.number(min=0).bind_value(state, 'investment').classes('w-full')
                                
                                # Ползунок спреда
                                with ui.column().classes('flex-1'):
                                    ui.label("Spread Range (%)").classes('text-xs font-bold text-slate-400')
                                    with ui.row().classes('w-full gap-2 mb-2'):
                                        ui.number('Min', min=0, max=1000).bind_value(state.spread_range, 'min').classes('flex-1').props('dense outlined suffix="%"')
                                        ui.number('Max', min=0, max=1000).bind_value(state.spread_range, 'max').classes('flex-1').props('dense outlined suffix="%"')
                                    ui.range(min=0, max=1000.0, step=0.1).bind_value(state, 'spread_range').props('label-always snap label-color="black"').classes('w-full px-2')

                            ui.separator().classes('mb-4')
                            
                            # === НОВОЕ: Фильтр по Market Cap ===
                            with ui.row().classes('w-full gap-6 items-center mb-4'):
                                ui.switch('Filter by Market Cap').bind_value(state, 'filter_mcap_enabled').classes('text-slate-700 font-bold')
                                # Показываем инпут только если свитч включен
                                ui.number('Min Cap ($)', min=0).bind_value(state, 'min_mcap').bind_visibility_from(state, 'filter_mcap_enabled').classes('flex-1').props('outlined dense prefix="$"')

                            ui.separator().classes('mb-4')

                            with ui.row().classes('w-full gap-6'):
                                with ui.column().classes('flex-1'):
                                    ui.label("Exchanges").classes('text-xs font-bold text-slate-400')
                                    ui.select(DEFAULT_EXCHANGES, multiple=True).bind_value(state, 'selected_exchanges').props('use-chips use-input').classes('w-full')
                                with ui.column().classes('flex-1'):
                                    ui.label("Coins").classes('text-xs font-bold text-slate-400')
                                    coin_select = ui.select([], multiple=True, label="Search coins...").bind_value(state, 'selected_coins').props('use-chips use-input').classes('w-full')

                    # --- КАЛЬКУЛЯТОР ---
                    with ui.expansion('🧮 Profit Calculator', icon='calculate').classes('w-full bg-white rounded-xl shadow-sm border border-slate-200 mb-4'):
                         with ui.column().classes('p-6 w-full gap-4'):
                            with ui.row().classes('w-full gap-4 items-end'):
                                ui.number('Amount ($)', min=0).bind_value(calc_state, 'amount').classes('flex-1').props('outlined dense')
                                ui.number('Spread (%)', min=0).bind_value(calc_state, 'spread').classes('flex-1').props('outlined dense')
                                ui.number('Buy Fee (%)', min=0, step=0.01).bind_value(calc_state, 'fee_buy').classes('w-32').props('outlined dense suffix="%"')
                                ui.number('Sell Fee (%)', min=0, step=0.01).bind_value(calc_state, 'fee_sell').classes('w-32').props('outlined dense suffix="%"')
                                ui.number('Cycles', min=1, step=1).bind_value(calc_state, 'cycles').classes('w-24').props('outlined dense')
                            ui.separator()
                            with ui.row().classes('w-full gap-4 justify-between items-center'):
                                def get_calc_results():
                                    amt = calc_state['amount'] or 0; spr = calc_state['spread'] or 0
                                    f_buy = calc_state['fee_buy'] or 0; f_sell = calc_state['fee_sell'] or 0; cyc = calc_state['cycles'] or 1
                                    turnover = amt * cyc
                                    gross_profit = turnover * (spr / 100.0)
                                    total_fees_usd = turnover * ((f_buy + f_sell) / 100.0)
                                    net_profit = gross_profit - total_fees_usd
                                    net_roi = (net_profit / turnover * 100) if turnover > 0 else 0
                                    return turnover, total_fees_usd, net_profit, net_roi

                                with ui.row().classes('gap-4 flex-1'):
                                    with ui.element('div').classes('calc-result-box flex-1'):
                                        ui.label('TOTAL VOLUME').classes('calc-label')
                                        ui.label().bind_text_from(calc_state, 'amount', lambda x: f"${get_calc_results()[0]:,.2f}").classes('calc-value text-slate-700')
                                    with ui.element('div').classes('calc-result-box flex-1 bg-red-50 border-red-200'):
                                        ui.label('FEES').classes('calc-label text-red-800')
                                        ui.label().bind_text_from(calc_state, 'amount', lambda x: f"-${get_calc_results()[1]:.2f}").classes('calc-value text-red-600')
                                    with ui.element('div').classes('calc-result-box flex-1'):
                                        ui.label('NET PROFIT').classes('calc-label')
                                        ui.label().bind_text_from(calc_state, 'amount', lambda x: f"+${get_calc_results()[2]:.2f}").classes('calc-value')
                                    with ui.element('div').classes('calc-result-box w-32'):
                                        ui.label('ROI %').classes('calc-label')
                                        ui.label().bind_text_from(calc_state, 'amount', lambda x: f"{get_calc_results()[3]:.2f}%").classes('calc-value')

                    # --- ТАБЛИЦА (ui.table) ---
                    ui.label("LIVE OPPORTUNITIES").classes('text-xl font-black text-slate-800 tracking-tight')
                    
                    columns = [
                        {'name': 'symbol', 'label': 'PAIR', 'field': 'symbol', 'align': 'left', 'sortable': True},
                        {'name': 'spread', 'label': 'SPREAD', 'field': 'spread', 'align': 'left', 'sortable': True},
                        {'name': 'profit', 'label': 'PROFIT', 'field': 'profit', 'align': 'left', 'sortable': True},
                        {'name': 'buy_price', 'label': 'BUY PRICE', 'field': 'buy_price', 'align': 'left'},
                        {'name': 'sell_price', 'label': 'SELL PRICE', 'field': 'sell_price', 'align': 'left'},
                        {'name': 'route', 'label': 'ROUTE (BUY -> SELL)', 'field': 'route', 'align': 'center'},
                    ]

                    arb_table = ui.table(columns=columns, rows=[], pagination=20).classes('w-full bg-white shadow-sm rounded-xl border border-slate-200')
                    
                    arb_table.add_slot('body-cell-symbol', '''
                        <q-td :props="props">
                            <div class="flex items-center gap-2">
                                <q-avatar size="24px" color="grey-2" text-color="grey-8" font-size="12px">
                                    {{ props.value.charAt(0) }}
                                </q-avatar>
                                <span class="font-bold text-slate-700">{{ props.value }}</span>
                            </div>
                        </q-td>
                    ''')

                    arb_table.add_slot('body-cell-spread', '''
                        <q-td :props="props">
                            <span :class="props.value > 1.0 ? 'text-green-600' : 'text-amber-600'" class="text-base font-black mono">
                                {{ props.value.toFixed(2) }}%
                            </span>
                        </q-td>
                    ''')
                    
                    arb_table.add_slot('body-cell-profit', '''
                        <q-td :props="props">
                            <span class="text-slate-600 font-bold mono">${{ props.value.toFixed(2) }}</span>
                        </q-td>
                    ''')

                    arb_table.add_slot('body-cell-route', '''
                        <q-td :props="props">
                            <div class="flex items-center justify-center gap-2">
                                <a :href="props.row.link_buy" target="_blank" class="ex-badge badge-gray">
                                    {{ props.row.buy_ex }}
                                </a>
                                <q-icon name="arrow_forward" size="xs" color="grey-4" />
                                <a :href="props.row.link_sell" target="_blank" class="ex-badge badge-green">
                                    {{ props.row.sell_ex }}
                                </a>
                            </div>
                        </q-td>
                    ''')

                    def render_arbitrage():
                        if backend.DISCOVERED_COINS:
                            sorted_coins = sorted(list(backend.DISCOVERED_COINS))
                            if coin_select.options != sorted_coins:
                                coin_select.options = sorted_coins
                                coins_count_label.set_text(f"Scanning {len(sorted_coins)} pairs")

                        if not state.is_running: return

                        # === ПОДГОТОВКА ДАННЫХ ДЛЯ ФИЛЬТРАЦИИ ПО КАПЕ ===
                        # Создаем словарь {SYMBOL: MCAP} из данных CoinGecko для быстрого поиска
                        mcap_lookup = {}
                        if market_data.MARKET_DATA:
                            for c in market_data.MARKET_DATA:
                                # CoinGecko символы маленькие (btc), CCXT большие (BTC/USDT)
                                sym = c['symbol'].upper()
                                mcap_lookup[sym] = c.get('market_cap', 0) or 0

                        new_rows = []
                        min_spread = state.spread_range['min']
                        max_spread = state.spread_range['max']

                        for item in backend.GLOBAL_OPPORTUNITIES:
                            if state.selected_coins and item['symbol'] not in state.selected_coins: continue
                            if item['buy_ex'] not in state.selected_exchanges: continue
                            if item['sell_ex'] not in state.selected_exchanges: continue
                            if not (min_spread <= item['spread'] <= max_spread): continue
                            
                            # === ЛОГИКА ФИЛЬТРА КАПИТАЛИЗАЦИИ ===
                            if state.filter_mcap_enabled:
                                # Берем базовую монету из пары (BTC из BTC/USDT)
                                base_coin = item['symbol'].split('/')[0]
                                coin_mcap = mcap_lookup.get(base_coin, 0)
                                if coin_mcap < state.min_mcap:
                                    continue # Пропускаем, если капа маленькая

                            profit = (item['spread'] / 100.0) * state.investment
                            
                            new_rows.append({
                                'symbol': item['symbol'],
                                'spread': item['spread'],
                                'profit': profit,
                                'buy_price': item['buy_price'],
                                'sell_price': item['sell_price'],
                                'buy_ex': item['buy_ex'],
                                'sell_ex': item['sell_ex'],
                                'link_buy': get_trade_link(item['buy_ex'], item['symbol']),
                                'link_sell': get_trade_link(item['sell_ex'], item['symbol']),
                                'route': 'link' 
                            })

                        # === ИЗМЕНЕНИЕ: Увеличили лимит до 100 монет ===
                        arb_table.rows = new_rows[:100]

                # --- Вкладка 2: РЫНОК ---
                with ui.tab_panel(tab_market).classes('p-0 gap-4'):
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.label("MARKET OVERVIEW (Top 150)").classes('text-xl font-black text-slate-800 tracking-tight')
                        
                        # === НОВОЕ: Поиск ===
                        with ui.row().classes('items-center gap-2'):
                            ui.input(placeholder='Search Coin...').bind_value(market_search, 'text').props('dense outlined rounded append-icon=search').classes('w-64 bg-white')
                            ui.button('Refresh', icon='refresh', on_click=lambda: render_market()).props('flat dense color=grey')

                    market_grid = 'grid grid-cols-[50px_3fr_2fr_2fr_2fr_2fr] gap-4 items-center px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider'
                    with ui.row().classes(f'w-full bg-slate-100 rounded-lg {market_grid}'):
                        ui.label('#'); ui.label('COIN'); ui.label('PRICE'); ui.label('24h %'); ui.label('MCAP'); ui.label('VOL')
                    
                    market_container = ui.column().classes('w-full gap-1')
                    
                    def render_market():
                        market_container.clear()
                        data = market_data.MARKET_DATA
                        if not data:
                            with market_container: 
                                ui.label("Loading...").classes('w-full text-center text-slate-400 italic py-4')
                                ui.spinner('dots', size='lg', color='green')
                            return
                        
                        search_text = market_search['text'].lower()

                        for coin in data:
                            # === ФИЛЬТР ПОИСКА ===
                            if search_text:
                                if search_text not in coin['name'].lower() and search_text not in coin['symbol'].lower():
                                    continue

                            with market_container:
                                with ui.row().classes('w-full bg-white px-4 py-3 rounded-lg border-b border-slate-100 items-center grid grid-cols-[50px_3fr_2fr_2fr_2fr_2fr] gap-4 coin-row'):
                                    ui.label(str(coin.get('market_cap_rank', '-'))).classes('text-slate-400 mono text-xs')
                                    with ui.row().classes('items-center gap-3'):
                                        ui.image(coin.get('image', '')).classes('w-6 h-6 rounded-full')
                                        with ui.column().classes('gap-0'):
                                            ui.label(coin.get('name', 'Unknown')).classes('font-bold text-slate-700 text-sm')
                                            ui.label(coin.get('symbol', '').upper()).classes('text-xs text-slate-400 font-bold')
                                    
                                    # === ЦВЕТ ЦЕНЫ (Зеленый/Красный) ===
                                    change = coin.get('price_change_percentage_24h', 0) or 0
                                    price_color = 'text-green-600' if change >= 0 else 'text-red-600'
                                    ui.label(f"${coin.get('current_price', 0):,}").classes(f'mono font-bold {price_color}')
                                    
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
            if backend.GLOBAL_LAST_UPDATE > last_render_ts:
                render_arbitrage()
                last_render_ts = time.time()
            if tabs.value == 'MARKET OVERVIEW':
                # Рендерим маркет, только если он пустой или изменился поиск (упрощенно: можно добавить проверку на last update рынка)
                # Чтобы поиск работал "на лету", можно привязать on_change к инпуту, но тут рендер идет по таймеру
                if not market_container.default_slot.children:
                     render_market()

        # Привязываем рендер рынка к вводу текста (для мгновенного поиска)
        # Находим элемент инпута в дереве NiceGUI сложновато отсюда, поэтому
        # просто добавим проверку в таймер или используем on_change в самом инпуте (сделано выше через render_market() в on_click, но лучше бы реактивно)
        # Добавим реактивность:
        def on_search_change():
            render_market()
        
        # Находим инпут в коде выше и добавляем .on('input', on_search_change) - но это сложно в текущей структуре.
        # Проще проверять изменение стейта:
        last_search_text = ''
        def search_watcher():
            nonlocal last_search_text
            if market_search['text'] != last_search_text:
                render_market()
                last_search_text = market_search['text']
        
        ui.timer(0.5, ui_tick)
        ui.timer(0.3, search_watcher) # Следим за поиском