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

# --- WEBSOCKET IMPLEMENTATION (Omitted WS function definitions for brevity) ---
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
    # We will let the app run even if CCXT fails here, as the NameError is the main issue
    # sys.exit(1)

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
    # This is a critical point of failure, keeping the logging
    try:
        ohlcv = exchange.fetch_ohlcv(selected_symbol, timeframe, limit=limit)
        
        if not ohlcv:
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        
        for col in ['open', 'high', 'low', 'close']: 
            df.loc[:, col] = df[col] * USD_TO_INR_RATE
        
        return df.to_json(date_format='iso', orient='split')
        
    except Exception as e: 
        print(f"CRITICAL ERROR: CCXT fetch failed for {selected_symbol}. Error: {e}")
        return None

# --- NEW: Helper for Fake Mobile Content ---
def get_fake_content_cards():
    content = []
    for _ in range(2):
        content.append(html.Div(className='fake-card', children=[
            html.Div("Market Analysis", style={'color':'#888', 'fontSize':'0.8rem'}),
            html.H4("BTC Breaking Resistance?", style={'margin':'5px 0'}),
            html.Div(className='fake-chart')
        ]))
        content.append(html.Div(className='fake-card', children=[
            html.Div("Live Rates", style={'color':'#888', 'fontSize':'0.8rem', 'marginBottom':'10px'}),
            html.Div(className='fake-row', children=[
                html.Div(className='fake-coin', children=[html.Div(className='fake-icon'), "BTC"]),
                html.Span("$98,450", className='txt-green')
            ]),
            html.Div(className='fake-row', children=[
                html.Div(className='fake-coin', children=[html.Div(className='fake-icon'), "ETH"]),
                html.Span("$3,890", className='txt-green')
            ]),
            html.Div(className='fake-row', children=[
                html.Div(className='fake-coin', children=[html.Div(className='fake-icon'), "SOL"]),
                html.Span("$145", className='txt-red')
            ])
        ]))
        content.append(html.Div(className='fake-card', children=[
            html.Div("Latest News", style={'color':'#888', 'fontSize':'0.8rem', 'marginBottom':'5px'}),
            html.Div(className='fake-news-img'),
            html.H5("Crypto Adoption reaches all time high in Asia.", style={'margin':'0'})
        ]))
    return content


# --- NEW: WELCOME PAGE LAYOUT FUNCTION (Required by NameError) ---
def get_welcome_layout():
    return html.Div(className='welcome-container', children=[
        html.Div(className='welcome-nav', children=[
             html.Div("CRYPTO MASTER", className='welcome-brand'),
             html.Div(className='welcome-links', children=[
                 html.Button("ABOUT", id='about-link-btn'),
                 html.Button("CONTACT", id='contact-link-btn'),
             ])
        ]),
        html.Div(className='welcome-body', children=[
            html.Div(className='mobile-mockup-wrapper', children=[
                html.Div(className='mobile-frame', children=[
                    html.Div(className='mobile-notch'),
                    html.Div(className='mobile-screen', children=[
                        html.Div(className='scroll-container', children=get_fake_content_cards())
                    ])
                ])
            ]),
            html.Div(className='hero-section', children=[
                html.H1("Welcome To Our Company", className='hero-title'),
                html.P("Explore the world of cryptocurrency market analysis, real-time data, and advanced trading indicators in one professional terminal.", className='hero-subtitle'),
                html.Button("LOGIN", id='login-btn-main', className='login-btn-large')
            ])
        ]),
        html.Div(id='modal-container')
    ])


# --- DASHBOARD APP ---
app = Dash(__name__, title="Crypto Master Terminal", suppress_callback_exceptions=True)

# ... (Index String and Dashboard Layout functions omitted for brevity, assume they are correct) ...

# --- NEW/MODIFIED LAYOUT PLACEHOLDER ---
def get_dashboard_layout():
    # --- Truncated Layout for space, use your full layout here ---
    return html.Div([
        # Header, Tabs, etc.
        html.Div(className='app-footer', children=["Footer"]),
        dcc.Interval(id='interval-component', interval=500, n_intervals=0),
        dcc.Interval(id='market-interval', interval=10000, n_intervals=0),
        dcc.Store(id='timeframe-store', data={'tf': '1m', 'limit': 50}),
        dcc.Store(id='ws-data-store', data=LATEST_WS_PRICES),
        dcc.Store(id='ticker-data-store', data={}),
        dcc.Store(id='chart-data-cache', data={'df_json': None, 'symbol': None, 'tf': None, 'limit': None}),
    ])


# --- INITIAL LAYOUT ---
app.layout = html.Div([
    dcc.Store(id='login-state-store', data=False),
    # FIX: get_welcome_layout is now defined above.
    html.Div(id='page-content', children=get_welcome_layout()) 
])

# --- CALLBACKS (Assuming the rest of the optimized callbacks are present and correct) ---
# ... (All other callbacks go here) ...


# --- RUN ---
server = app.server 
if __name__ == '__main__':
    start_websocket_thread() 
    print(f"\n✅ Dashboard Live: http://127.0.0.1:{PORT}\n")
    app.run(debug=False, host='127.0.0.1', port=PORT)
