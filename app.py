import pandas as pd
import plotly.graph_objects as go
import ccxt
import sys
import time
import locale
import socket
import dash
import json
import random
import numpy as np
import threading
import websocket
from datetime import datetime, timedelta
from dash import Dash, dcc, html, ctx
from dash.dependencies import Input, Output, State, ALL

# --- STEP 1: NETWORK UTILS ---
def get_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

# --- CONFIGURATION ---
EXCHANGE_ID = 'binance'
USD_TO_INR_RATE = 84.00
PORT = 8089 

SYMBOL_MAP = {
    'BTC/USDT': 'Bitcoin', 'ETH/USDT': 'Ethereum', 'BNB/USDT': 'Binance Coin',
    'SOL/USDT': 'Solana', 'XRP/USDT': 'XRP', 'DOGE/USDT': 'Dogecoin',
    'ADA/USDT': 'Cardano', 'TRX/USDT': 'TRON', 'AVAX/USDT': 'Avalanche',
    'SHIB/USDT': 'ShIBa Inu'
}

COIN_PARAMS = {
    'BTC/USDT': {'supply': 19_640_000, 'symbol': 'BTC', 'max': 21000000},
    'ETH/USDT': {'supply': 120_000_000, 'symbol': 'ETH', 'max': None},
    'BNB/USDT': {'supply': 153_000_000, 'symbol': 'BNB', 'max': 200000000},
    'SOL/USDT': {'supply': 440_000_000, 'symbol': 'SOL', 'max': None},
    'XRP/USDT': {'supply': 54_000_000_000, 'symbol': 'XRP', 'max': 100000000000},
    'DOGE/USDT': {'supply': 143_000_000_000, 'symbol': 'DOGE', 'max': None},
    'ADA/USDT': {'supply': 35_000_000_000, 'symbol': 'ADA', 'max': 45000000000},
    'TRX/USDT': {'supply': 88_000_000_000, 'symbol': 'TRX', 'max': None},
    'AVAX/USDT': {'supply': 377_000_000, 'symbol': 'AVAX', 'max': 720000000},
    'SHIB/USDT': {'supply': 589_000_000_000_000, 'symbol': 'SHIB', 'max': None}
}

TRACKER_SYMBOLS = list(SYMBOL_MAP.keys())
DROPDOWN_OPTIONS = [{'label': SYMBOL_MAP[s], 'value': s} for s in TRACKER_SYMBOLS]
DEFAULT_SYMBOL = 'BTC/USDT'

# --- GLOBAL LIVE DATA STORE (Updated by WebSocket Thread) ---
LATEST_WS_PRICES = {symbol: 0.0 for symbol in SYMBOL_MAP.keys()}
LATEST_WS_PRICES[DEFAULT_SYMBOL] = 70000 * USD_TO_INR_RATE 

# --- WEBSOCKET IMPLEMENTATION ---
BINANCE_WS_BASE_URL = "wss://stream.binance.com:9443/ws/"
WS_STREAMS = "/".join([f"{s.lower().replace('/', '')}@trade" for s in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']]) 
BINANCE_WS_URL = f"{BINANCE_WS_BASE_URL}{WS_STREAMS}"

def on_message(ws, message):
    global LATEST_WS_PRICES
    try:
        data = json.loads(message)
        trade_data = data.get('data', data)
        
        if 'p' in trade_data and 's' in trade_data:
            symbol_ws = trade_data['s']
            symbol_ccxt = f"{symbol_ws[:3]}/{symbol_ws[3:]}"
            
            if symbol_ccxt in LATEST_WS_PRICES:
                price = float(trade_data['p'])
                LATEST_WS_PRICES[symbol_ccxt] = price * USD_TO_INR_RATE
    except Exception as e:
        pass

def on_error(ws, error):
    print(f"WS Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WS Closed")

def on_open(ws):
    print(f"✅ WebSocket Connection Opened to Binance for {WS_STREAMS}")

def start_websocket_thread():
    ws = websocket.WebSocketApp(
        BINANCE_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    wst = threading.Thread(target=ws.run_forever, kwargs={'ping_interval': 30, 'ping_timeout': 10})
    wst.daemon = True
    wst.start()
    print("✅ WebSocket Thread Started.")

# --- CCXT INITIALIZATION (For historical data only) ---
try: 
    exchange = getattr(ccxt, EXCHANGE_ID)({'options': {'verify': False}})
    exchange.load_markets()
    print(f"✅ CCXT ({EXCHANGE_ID}) initialized.")
except Exception as e: 
    print(f"⚠️ Error initializing exchange. Error: {e}")
    sys.exit(1)

try: locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
except: pass

# --- HELPERS (Formatting, etc.) ---
def format_currency(value):
    try: return locale.currency(value, symbol='₹', grouping=True)
    except: return f'₹ {value:,.2f}'

def format_compact(value):
    if value >= 1_000_000_000_000: return f"₹{value/1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000: return f"₹{value/1_000_000_000:.2f}B"
    if value >= 1_000_000: return f"₹{value/1_000_000:.2f}M"
    return f"₹{value:,.0f}"

def get_icon_url(symbol):
    base = symbol.split('/')[0].lower()
    return f"https://assets.coincap.io/assets/icons/{base}@2x.png"

# --- DATA FETCHING (REST API for OHLCV/Historical) ---
def fetch_chart_data(selected_symbol, timeframe, limit):
    print(f"DIAG: Attempting to fetch OHLCV for {selected_symbol} ({timeframe}, limit={limit})...")
    try:
        ohlcv = exchange.fetch_ohlcv(selected_symbol, timeframe, limit=limit)
        
        if not ohlcv:
            print(f"DIAG: CCXT returned no data for {selected_symbol}.")
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        
        for col in ['open', 'high', 'low', 'close']: 
            df.loc[:, col] = df[col] * USD_TO_INR_RATE
        
        print(f"DIAG: CCXT fetch successful. Rows: {len(df)}")
        # Convert DataFrame to JSON string for storage
        return df.to_json(date_format='iso', orient='split')
        
    except Exception as e: 
        print(f"CRITICAL ERROR: CCXT fetch failed for {selected_symbol}. Error: {e}")
        return None

# --- DASHBOARD APP ---
app = Dash(__name__, title="Crypto Master Terminal", suppress_callback_exceptions=True)

# --- LAYOUT (Truncated for brevity) ---
def get_dashboard_layout():
    return html.Div([
        # --- HEADER / NAVBAR ---
        html.Div(className='navbar', children=[
            html.Div(className='nav-brand', children=[
                html.Span("⚡"),
                html.Span("CRYPTO MASTER")
            ]),
            html.Div(className='nav-controls', children=[
                html.Span("Quick Select:", className='nav-label'),
                dcc.Dropdown(
                    id='coin-select-dropdown', 
                    options=DROPDOWN_OPTIONS, 
                    value=DEFAULT_SYMBOL, 
                    clearable=False, 
                    style={'backgroundColor': '#ffffff', 'color': '#000000', 'borderRadius': '5px', 'width': '200px'}
                ),
            ])
        ]),
        
        dcc.Tabs(parent_className='custom-tabs', className='custom-tabs-container', children=[
            
            dcc.Tab(label='Chart', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(style={'marginTop': '20px'}),
                html.H2(id='live-price-display', className='live-price-big'),
                html.Div(className='flex-container', children=[
                    html.Div(className='chart-wrapper', children=[
                        html.Div(className='control-bar-container', children=[
                            html.Div(className='btn-group', children=[html.Button("Price", className='control-btn active'), html.Button("Market Cap", className='control-btn'), html.Button("TradingView", className='control-btn')]),
                            html.Div(className='btn-group', children=[html.Button("LIVE", id={'type': 'tf-btn', 'index': 'LIVE'}, className='control-btn live-btn active'), html.Button("24H", id={'type': 'tf-btn', 'index': '24H'}, className='control-btn'), html.Button("7D", id={'type': 'tf-btn', 'index': '7D'}, className='control-btn'), html.Button("1M", id={'type': 'tf-btn', 'index': '1M'}, className='control-btn'), html.Button("1Y", id={'type': 'tf-btn', 'index': '1Y'}, className='control-btn'), html.Button("5Y", id={'type': 'tf-btn', 'index': '5Y'}, className='control-btn')])
                        ]),
                        html.Div(style={'padding': '15px'}, children=[html.H3(id='chart-title', style={'borderBottom': '1px solid #333', 'paddingBottom': '10px', 'marginTop': '0'}), dcc.Graph(id='live-candlestick-chart', style={'height': '450px'})])
                    ]),
                    html.Div(className='metrics-container', children=[html.Div(id='key-metrics-panel')]),
                ]),
                # Bar chart relies on Ticker Store, not real-time interval
                html.Div(className='bottom-bar-chart', children=[html.H4("Top 10 Crypto Performance (24h)", style={'color': '#DDD'}), dcc.Graph(id='bar-chart-24h', style={'height': '300px'})])
            ]),
            # ... (Other Tabs omitted for brevity, keeping only essential components) ...
        ]),
        
        # --- FOOTER ---
        html.Div(className='app-footer', children=[
            html.Div("© 2025 Crypto Master Terminal. All rights reserved.", className='footer-text'),
            html.Div("Data provided by Binance & Simulated Feeds for Demo.", style={'color': '#444'})
        ]),

        # --- STORES & INTERVALS ---
        dcc.Interval(id='interval-component', interval=500, n_intervals=0), # FAST interval for WS price
        dcc.Interval(id='market-interval', interval=10000, n_intervals=0), # SLOW interval for Ticker/Market update
        dcc.Store(id='timeframe-store', data={'tf': '1m', 'limit': 50}),
        dcc.Store(id='ws-data-store', data=LATEST_WS_PRICES),
        dcc.Store(id='ticker-data-store', data={}), # NEW: Slow Ticker Data
        dcc.Store(id='chart-data-cache', data={'df_json': None, 'symbol': None, 'tf': None, 'limit': None}), # NEW: Chart Data Cache
        dcc.Store(id='login-state-store', data=False),
        dcc.Store(id='current-page-store', data=1)
    ])

# --- INITIAL LAYOUT ---
app.layout = html.Div([
    html.Div(id='page-content', children=get_welcome_layout())
])

# --- CALLBACKS ---

# (Login/Modal callbacks omitted for brevity, assuming they are working)

@app.callback(
    Output('ws-data-store', 'data'),
    Input('interval-component', 'n_intervals'),
    prevent_initial_call=True
)
def update_ws_store(n):
    return LATEST_WS_PRICES

# --- NEW SLOW CALLBACK: FETCH TICKET DATA ---
@app.callback(
    [Output('ticker-data-store', 'data'),
     Output('bar-chart-24h', 'figure', allow_duplicate=True)],
    Input('market-interval', 'n_intervals'),
    prevent_initial_call=True
)
def update_ticker_and_bar_chart(n):
    print(f"DIAG: Running SLOW Ticker/Bar Chart update (Interval: {n})")
    ticker_data_all = {}
    fig_bar = go.Figure()
    
    try:
        tickers = exchange.fetch_tickers(TRACKER_SYMBOLS)
        bar_x, bar_y, bar_colors = [], [], []
        
        for symbol in TRACKER_SYMBOLS:
            if symbol in tickers:
                t = tickers[symbol]
                
                # Store ticker data
                ticker_data_all[symbol] = {
                    'percentage': t['percentage'],
                    'quoteVolume': t['quoteVolume'],
                    'last': t['last']
                }
                
                # Prepare Bar Chart data
                name = SYMBOL_MAP.get(symbol, symbol); p_change = t['percentage']
                bar_x.append(name); bar_y.append(p_change); bar_colors.append('#00CC96' if p_change >= 0 else '#FF4136')

        # Generate Bar Chart
        if bar_x: 
            zipped = sorted(zip(bar_x, bar_y, bar_colors), key=lambda x: x[1], reverse=True)
            bar_x, bar_y, bar_colors = zip(*zipped)
            fig_bar = go.Figure(go.Bar(x=bar_x, y=bar_y, marker_color=bar_colors, text=[f"{y:.2f}%" for y in bar_y], textposition='auto'))
            fig_bar.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(title='24h Change %', showgrid=True, gridcolor='#333'), xaxis=dict(showgrid=False))

    except Exception as e:
        print(f"CRITICAL ERROR: Slow Ticker/Bar Chart Fetch failed: {e}")
        
    return ticker_data_all, fig_bar

# --- NEW INTERMEDIATE CALLBACK: CACHE/UPDATE CHART DATA (runs when TF changes) ---
@app.callback(
    Output('chart-data-cache', 'data'),
    [Input('timeframe-store', 'data'),
     Input('coin-select-dropdown', 'value')],
    State('chart-data-cache', 'data')
)
def manage_chart_data_cache(tf_data, selected_symbol, cache_data):
    if not selected_symbol:
        return {'df_json': None, 'symbol': None, 'tf': None, 'limit': None}
        
    # Check if we already have the data for this symbol/timeframe
    if (selected_symbol == cache_data['symbol'] and 
        tf_data['tf'] == cache_data['tf'] and 
        tf_data['limit'] == cache_data['limit']):
        
        # If LIVE mode, we only need the historical data once, then use cache
        if tf_data['tf'] == '1m' and cache_data['df_json'] is not None:
            print("DIAG: Serving 1m chart data from cache.")
            return cache_data # No need to refetch
        
        if tf_data['tf'] != '1m' and cache_data['df_json'] is not None:
            print("DIAG: Serving historical chart data from cache.")
            return cache_data # No need to refetch
            
    # If parameters changed or cache is empty, FETCH NEW DATA (Slow Operation)
    print("DIAG: Cache Miss/Parameters Changed. Triggering new CCXT fetch...")
    
    df_json = fetch_chart_data(selected_symbol, tf_data['tf'], tf_data['limit'])
    
    return {
        'df_json': df_json,
        'symbol': selected_symbol,
        'tf': tf_data['tf'],
        'limit': tf_data['limit']
    }

# --- MAIN FAST CALLBACK: RENDER CHART (Uses cached data) ---
@app.callback(
    [Output('live-candlestick-chart', 'figure'),
     Output('live-price-display', 'children'),
     Output('key-metrics-panel', 'children'),
     Output('chart-title', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('coin-select-dropdown', 'value'),
     Input('timeframe-store', 'data'),
     Input('ws-data-store', 'data'),
     Input('ticker-data-store', 'data'), # Slow data for metrics
     Input('chart-data-cache', 'data')] # Cached historical data
)
def update_overview_fast(n, selected_symbol, tf_data, ws_data, ticker_data, cache_data):
    
    print(f"DIAG: Running FAST Chart Update (Interval: {n}). Cache status: {cache_data['df_json'] is not None}")
    
    if not selected_symbol or cache_data['df_json'] is None: 
        return go.Figure(), "Loading...", "Loading Metrics", "Loading Chart"
        
    # Load DataFrame from cached JSON
    try:
        df = pd.read_json(cache_data['df_json'], orient='split')
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    except:
        return go.Figure(), "N/A", "Data Error", "Chart Error"

    # --- 1. GET LIVE PRICE ---
    latest_price = ws_data.get(selected_symbol, df['close'].iloc[-1])
    
    # --- 2. GET SLOW TICKET DATA ---
    current_ticker = ticker_data.get(selected_symbol, {})
    pct_change = current_ticker.get('percentage', 0)
    volume_usd = current_ticker.get('quoteVolume', 0) # This is USD Volume
    volume = volume_usd * USD_TO_INR_RATE
    
    # 3. FIX CHART FOR LIVE VIEW
    if tf_data['tf'] == '1m':
        # Safely update the last close price for real-time visualization
        last_index = df.index[-1]
        df.loc[last_index, 'close'] = latest_price 
        
    # --- 4. CALCULATE METRICS ---
    color = '#00CC96' if pct_change >= 0 else '#FF4136'
    full_name = SYMBOL_MAP.get(selected_symbol, selected_symbol)
    supply = COIN_PARAMS.get(selected_symbol, {'supply': 0, 'max': 0, 'symbol': 'Crypto'})
    market_cap = latest_price * supply['supply'] / USD_TO_INR_RATE
    fdv = latest_price * supply['max'] / USD_TO_INR_RATE if supply['max'] else market_cap

    metrics_html = [
        # ... (Metrics HTML generation using latest_price and current_ticker) ...
        html.Div(className='market-cap-card', children=[html.Div("Market Cap ⓘ", className='metric-title'), html.Div(format_compact(market_cap), className='metric-value-large'), html.Div(f"{pct_change:+.2f}%", style={'color': color, 'fontSize': '0.9rem', 'marginTop': '5px'})]), 
        # (rest of your metrics HTML for key-metrics-panel)
        html.Div("Metrics Panel Placeholder (Optimized)")
    ]
    
    # 5. RENDER CHART
    fig_candle = go.Figure(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00CC96', decreasing_line_color='#FF4136', name='Price'))
    df.loc[:, 'SMA'] = df['close'].rolling(5).mean() 
    fig_candle.add_trace(go.Scatter(x=df['timestamp'], y=df['SMA'], line=dict(color='white', width=1), name='SMA (Trend)'))
    fig_candle.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=0, r=40, t=10, b=20), yaxis=dict(gridcolor='#333'), xaxis=dict(gridcolor='#333'), hovermode='x unified', hoverlabel=dict(bgcolor="#1e1e1e", font_size=12, font_color="white", bordercolor="#333"))
    
    price_html = html.Span(f"Live Price: {format_currency(latest_price)}", style={'color': color})
    
    title_suffix = "LIVE VIEW (Last 50 Mins)" if tf_data['tf'] == '1m' else "Past 24 Hours"
    return fig_candle, price_html, metrics_html, f"{full_name} Analysis - {title_suffix}"

# (Remaining callbacks like update_controls, update_market_trending_news_dex, etc., remain the same)
# NOTE: You will need to add the Ticker Store input to your other slow callbacks (like market table, analytics, etc.) as well to use the cached ticker data.

# --- RUN ---
server = app.server 
if __name__ == '__main__':
    start_websocket_thread() 
    print(f"\n✅ Dashboard Live: http://127.0.0.1:{PORT}\n")
    app.run(debug=False, host='127.0.0.1', port=PORT)
