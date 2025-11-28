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
from io import StringIO
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

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

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

DEX_CATEGORIES = {
    'BSC 🟡': ['BNB/USDT', 'ADA/USDT', 'XRP/USDT'],
    'Solana 🟣': ['SOL/USDT', 'AVAX/USDT', 'TRX/USDT'],
    'Meme 🐶': ['DOGE/USDT', 'SHIB/USDT', 'BTC/USDT'],
    'AI 🤖': ['ETH/USDT', 'BNB/USDT', 'SOL/USDT'],
    'PerpDEX 📈': ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']
}

UPCOMING_PROJECTS = [
    {'name': 'DeepSnitch AI', 'symbol': 'DSNT', 'category': 'AI Agent', 'price': '$0.024', 'raised': '85%', 'target': '$1M', 'desc': 'AI-powered trading surveillance for retail investors.'},
    {'name': 'Best Wallet', 'symbol': 'BEST', 'category': 'DeFi Wallet', 'price': '$0.089', 'raised': '92%', 'target': '$15M', 'desc': 'Next-gen Web3 wallet with zero-fee DEX aggregation.'},
    {'name': 'Bitcoin Hyper', 'symbol': 'HYPER', 'category': 'Layer 2', 'price': '$0.005', 'raised': '45%', 'target': '$5M', 'desc': 'High-speed Bitcoin Layer 2 solution using ZK-Rollups.'},
    {'name': 'Tapzi', 'symbol': 'TAP', 'category': 'GameFi', 'price': '$0.012', 'raised': '60%', 'target': '$2M', 'desc': 'Play-to-earn gaming ecosystem on Solana.'},
    {'name': 'EcoChain', 'symbol': 'ECO', 'category': 'RWA', 'price': '$0.150', 'raised': '20%', 'target': '$10M', 'desc': 'Real-world asset tokenization for green energy projects.'},
    {'name': 'MemeFi', 'symbol': 'MEME', 'category': 'Meme', 'price': '$0.0004', 'raised': '98%', 'target': '$500K', 'desc': 'Viral meme coin with built-in staking rewards.'}
]

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
    pass

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

# --- CCXT INITIALIZATION ---
try: 
    exchange = getattr(ccxt, EXCHANGE_ID)({'options': {'verify': False}})
    exchange.load_markets()
    print(f"✅ CCXT ({EXCHANGE_ID}) initialized.")
except Exception as e: 
    print(f"⚠️ Error initializing exchange. Error: {e}")
    # Continue execution, dashboard will handle data failures gracefully
    pass

try: locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
except: pass

# --- HELPERS ---
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

def get_tradingview_html(symbol):
    tv_symbol = f"BINANCE:{symbol.replace('/', '')}"
    return f"""<!DOCTYPE html><html><head><style>body, html {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #1e1e1e; }}</style></head><body><div class="tradingview-widget-container" style="height:100%;width:100%"><div id="tradingview_widget"></div><script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script><script type="text/javascript">new TradingView.widget({{"autosize": true, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Asia/Kolkata", "theme": "dark", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_widget", "details": true, "hotlist": true, "calendar": true, "hide_side_toolbar": false}});</script></div></body></html>"""

# --- DATA FETCHING ---
def fetch_chart_data(selected_symbol, timeframe, limit):
    print(f"DIAG: Fetching OHLCV for {selected_symbol} ({limit})...")
    try:
        ohlcv = exchange.fetch_ohlcv(selected_symbol, timeframe, limit=limit)
        if not ohlcv: return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        for col in ['open', 'high', 'low', 'close']: 
            df.loc[:, col] = df[col] * USD_TO_INR_RATE
        # Return JSON string to avoid SettingWithCopyWarning in future manipulations
        return df.to_json(date_format='iso', orient='split')
    except Exception as e: 
        print(f"ERROR: CCXT fetch failed: {e}")
        return None

def fetch_market_data():
    data = []
    try:
        tickers = exchange.fetch_tickers()
        all_pairs = [s for s in tickers.keys() if s.endswith('/USDT')]
        top_pairs = sorted(all_pairs, key=lambda x: tickers[x]['quoteVolume'], reverse=True)[:100]
        
        for i, symbol in enumerate(top_pairs):
            t = tickers[symbol]
            base_coin = symbol.split('/')[0]
            price_usd = t['last']
            price = LATEST_WS_PRICES.get(symbol, price_usd * USD_TO_INR_RATE)
            volume = t['quoteVolume'] * USD_TO_INR_RATE
            change_24h = t['percentage']
            supply = COIN_PARAMS.get(symbol, {}).get('supply', 0)
            mkt_cap = price * (supply/USD_TO_INR_RATE) if supply > 0 else volume * 10 
            
            history = []
            val = price
            trend = 1 if change_24h >= 0 else -1
            for _ in range(15):
                val = val * (1 + random.uniform(-0.02, 0.02) * trend)
                history.append(val)
            history.append(price)
            
            data.append({'rank': i + 1, 'symbol': symbol, 'name': base_coin, 'price': price, 'mkt_cap': mkt_cap, 'volume': volume, 'change_24h': change_24h, 'change_7d': change_24h * 1.2, 'history': history})
    except Exception as e: pass
    return data

def calculate_advanced_metrics(df):
    if df is None or len(df) < 350: return None, None, None, None
    df.loc[:, '111DMA'] = df['close'].rolling(window=111).mean()
    df.loc[:, '350DMA'] = df['close'].rolling(window=350).mean() * 2
    df.loc[:, 'log_price'] = np.log(df['close'])
    df.loc[:, 'Rainbow_Base'] = df['close'].rolling(window=100).mean() 
    df.loc[:, '365DMA'] = df['close'].rolling(window=365).mean()
    df.loc[:, 'Puell'] = df['close'] / df['365DMA']
    current_puell = df['Puell'].iloc[-1]
    puell_meter_val = min(max((current_puell - 0.5) / (3.0 - 0.5) * 100, 0), 100)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df.loc[:, 'RSI'] = 100 - (100 / (1 + rs))
    current_rsi = df['RSI'].iloc[-1]
    price_to_pi = df['close'].iloc[-1] / df['350DMA'].iloc[-1]
    top_score = (price_to_pi * 0.6 + (current_rsi/100) * 0.4) * 100
    top_score = min(top_score, 100)
    return df, current_puell, puell_meter_val, top_score

def generate_global_market_data():
    try:
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=365)
        if not ohlcv: return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        for col in ['open', 'high', 'low', 'close']: df.loc[:, col] = df[col] * USD_TO_INR_RATE
        btc_supply = 19_600_000
        total_mkt_cap = df['close'] * btc_supply * 2.0 
        total_volume = df['volume'] * 10000 * 5
        return df['timestamp'], total_mkt_cap, total_volume
    except: return None

def generate_crypto_news():
    headlines = ["Bitcoin Surges Past Key Resistance", "Ethereum 2.0 Upgrade Details", "Solana Network Record Transactions", "Crypto Regulation New Bill", "Binance New Partnership", "XRP Ledger Activity Spikes", "Top 5 Altcoins to Watch", "Global Crypto Adoption Growth"]
    sources = ["CoinDesk", "CoinTelegraph", "Decrypt", "Bloomberg", "CryptoSlate"]
    images = ["https://images.unsplash.com/photo-1518546305927-5a555bb7020d?auto=format&fit=crop&w=500&q=60", "https://images.unsplash.com/photo-1621761191319-c6fb62004040?auto=format&fit=crop&w=500&q=60", "https://images.unsplash.com/photo-1622630998477-20aa696fab05?auto=format&fit=crop&w=500&q=60"]
    news_items = []
    random.shuffle(headlines)
    for i in range(6):
        item = {'title': headlines[i], 'source': random.choice(sources), 'time': f"{random.randint(1, 59)} mins ago", 'image': random.choice(images), 'desc': "The cryptocurrency market is witnessing significant movement today..."}
        news_items.append(item)
    return news_items

# --- HELPER: FAKE CONTENT FOR WELCOME SCREEN ---
def get_fake_content_cards():
    content = []
    for _ in range(2):
        content.append(html.Div(className='fake-card', children=[
            html.Div("Market Analysis", style={'color':'#888', 'fontSize':'0.7rem'}),
            html.H5("BTC Breaking Resistance?", style={'margin':'5px 0', 'color':'white', 'fontSize':'0.9rem'}),
            html.Div(className='fake-chart')
        ]))
        content.append(html.Div(className='fake-card', children=[
            html.Div("Live Rates", style={'color':'#888', 'fontSize':'0.7rem', 'marginBottom':'8px'}),
            html.Div(className='fake-row', children=[
                html.Div(className='fake-coin', children=[html.Div("B", className='fake-icon-txt', style={'background':'#F7931A'}), "BTC"]),
                html.Span("$98,450", className='txt-green')
            ]),
             html.Div(className='fake-row', children=[
                html.Div(className='fake-coin', children=[html.Div("S", className='fake-icon-txt', style={'background':'#00FFA3', 'color':'black'}), "SOL"]),
                html.Span("$145", className='txt-red')
            ])
        ]))
    return content

# --- WELCOME PAGE LAYOUT FUNCTION ---
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
            html.Div(className='hero-section', children=[
                html.H1("Welcome To Our Company", className='hero-title'),
                html.P("Explore the world of cryptocurrency market analysis, real-time data, and advanced trading indicators in one professional terminal.", className='hero-subtitle'),
                html.Button("LOGIN", id='login-btn-main', className='login-btn-large')
            ]),
            html.Div(className='mobile-mockup-wrapper', children=[
                html.Div(className='mobile-frame', children=[
                    html.Div(className='mobile-notch'),
                    html.Div(className='mobile-screen', children=[
                        html.Div(className='scroll-container', children=get_fake_content_cards())
                    ])
                ])
            ])
        ]),
        html.Div(id='modal-container')
    ])

# --- DASHBOARD APP ---
app = Dash(__name__, title="Crypto Master Terminal", suppress_callback_exceptions=True)

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Crypto Master Terminal</title>
        {%css%}
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;900&display=swap');
            body { background-color: #121212; color: #e0e0e0; font-family: 'Poppins', sans-serif; margin: 0; padding: 0; }
            .welcome-container { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(circle at top right, #0a192f 0%, #020c1b 60%, #000000 100%); z-index: 2000; display: flex; flex-direction: column; color: white; overflow: hidden; }
            .welcome-container::before { content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px); background-size: 50px 50px; pointer-events: none; }
            .welcome-nav { display: flex; justify-content: space-between; align-items: center; padding: 25px 60px; flex-shrink: 0; z-index: 2; }
            .welcome-brand { font-size: 1.5rem; font-weight: 900; letter-spacing: 1px; color: white; }
            .welcome-links button { background: transparent; border: none; color: #aaa; margin-left: 30px; padding: 5px 10px; cursor: pointer; font-weight: 600; font-size: 0.8rem; letter-spacing: 1px; transition: 0.3s; }
            .welcome-links button:hover { color: #00CC96; }
            .welcome-body { flex: 1; display: flex; align-items: center; justify-content: space-between; padding: 0 80px 50px 80px; gap: 80px; z-index: 2; }
            .hero-section { flex: 1; max-width: 550px; }
            .hero-title { font-size: 4rem; font-weight: 900; margin-bottom: 25px; line-height: 1.1; color: white; }
            .hero-subtitle { font-size: 1.1rem; color: #8892b0; margin-bottom: 40px; line-height: 1.6; }
            .login-btn-large { background: linear-gradient(90deg, #00CC96, #00a8ff); border: none; color: white; padding: 15px 50px; font-size: 1rem; font-weight: bold; border-radius: 30px; cursor: pointer; transition: transform 0.3s, box-shadow 0.3s; width: fit-content; box-shadow: 0 5px 20px rgba(0, 204, 150, 0.3); letter-spacing: 1px; }
            .login-btn-large:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0, 204, 150, 0.5); }
            .mobile-mockup-wrapper { flex: 0 0 auto; display: flex; justify-content: center; align-items: center; height: 100%; perspective: 1000px; }
            .mobile-frame { width: 280px; height: 580px; background: #050505; border-radius: 45px; border: 10px solid #1a1a1a; box-shadow: -20px 20px 60px rgba(0,0,0,0.7), 0 0 20px rgba(0, 204, 150, 0.2); position: relative; overflow: hidden; transform: rotateY(-10deg) rotateX(5deg); }
            .mobile-notch { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 100px; height: 25px; background: #1a1a1a; border-bottom-left-radius: 18px; border-bottom-right-radius: 18px; z-index: 10; }
            .mobile-screen { width: 100%; height: 100%; background: #0a0a0a; overflow: hidden; position: relative; padding-top: 40px; }
            .scroll-container { display: flex; flex-direction: column; padding: 0 15px; animation: scrollUp 12s linear infinite; }
            @keyframes scrollUp { 0% { transform: translateY(0); } 100% { transform: translateY(-33.33%); } }
            .fake-card { background: #141414; border-radius: 16px; margin-bottom: 15px; padding: 15px; border: 1px solid #222; }
            .fake-chart { height: 40px; background: linear-gradient(90deg, #141414, #00CC96, #141414); position: relative; overflow: hidden; border-radius: 8px; margin-top: 10px; opacity: 0.5; }
            .fake-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.75rem; }
            .fake-coin { display: flex; align-items: center; gap: 8px; color: white; font-weight: bold; }
            .fake-icon-txt { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.6rem; font-weight: 900; }
            .txt-green { color: #00CC96; font-weight: bold; } .txt-red { color: #FF4136; font-weight: bold; }
            
            /* --- MODAL STYLES (UPDATED) --- */
            .modal-overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.85); z-index: 9999;
                display: flex; justify-content: center; align-items: center;
                backdrop-filter: blur(8px); animation: fadeIn 0.3s;
            }
            .modal-content {
                background: #161a1e; padding: 40px; border-radius: 20px;
                border: 1px solid #00CC96;
                text-align: center; position: relative; max-width: 450px; width: 90%;
                box-shadow: 0 0 50px rgba(0, 204, 150, 0.2);
                color: #e0e0e0;
            }
            .modal-close {
                position: absolute; top: 15px; right: 20px; 
                font-size: 2rem; font-weight: bold; cursor: pointer; color: #888; 
                transition: 0.2s; line-height: 1; z-index: 10000;
            }
            .modal-close:hover { color: #FF4136; transform: scale(1.2); }
            
            .profile-pic {
                width: 130px; height: 130px; border-radius: 50%; object-fit: cover;
                border: 4px solid #00CC96; margin-bottom: 20px;
                box-shadow: 0 0 25px rgba(0, 204, 150, 0.4);
            }
            
            .contact-info-box h3 { color: #fff; margin-bottom: 25px; font-size: 1.5rem; }
            .contact-item { margin-bottom: 15px; color: #aaa; font-size: 0.95rem; display: flex; flex-direction: column; gap: 5px; }
            .contact-label { font-weight: 600; color: #00CC96; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
            .contact-val { color: white; font-weight: 500; }
            .contact-link { color: #00a8ff; text-decoration: none; font-weight: bold; transition: 0.2s; }
            .contact-link:hover { color: #00CC96; text-decoration: underline; }
            .about-text p { line-height: 1.6; margin-bottom: 15px; color: #ccc; }
            
            /* --- DASHBOARD STYLES --- */
            .navbar { display: flex; justify-content: space-between; align-items: center; background-color: #161a1e; padding: 15px 30px; border-bottom: 1px solid #2a2e39; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            .nav-brand { font-size: 1.8rem; font-weight: 900; color: #F0B90B; display: flex; align-items: center; gap: 10px; letter-spacing: 1px; }
            .nav-controls { display: flex; align-items: center; gap: 15px; }
            .nav-label { color: #888; font-size: 0.9rem; }
            .custom-tabs-container { margin-top: 0; }
            .custom-tabs { border-bottom: 1px solid #333; background: #121212; }
            .custom-tab { background-color: #121212; color: #888; border: none; padding: 15px 25px; font-size: 1rem; cursor: pointer; border-bottom: 2px solid transparent; transition: 0.3s; }
            .custom-tab--selected { background-color: #121212; color: #F0B90B !important; border-bottom: 2px solid #F0B90B; font-weight: bold; }
            .app-footer { text-align: center; padding: 40px 20px; color: #555; font-size: 0.85rem; border-top: 1px solid #222; margin-top: 40px; background-color: #161a1e; }
            .control-bar-container { display: flex; justify-content: space-between; align-items: center; background-color: #1e1e1e; padding: 10px 20px; border-radius: 8px 8px 0 0; margin-top: 20px; border-bottom: 1px solid #333; }
            .btn-group { display: flex; background-color: #2a2a2a; border-radius: 6px; padding: 3px; gap: 2px; }
            .control-btn { background-color: transparent; border: none; color: #888; padding: 6px 15px; font-size: 0.9rem; cursor: pointer; border-radius: 4px; font-weight: bold; transition: 0.2s; }
            .control-btn:hover { color: #fff; background-color: #333; }
            .control-btn.active { background-color: #fff; color: #000; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
            .control-btn.live-btn { color: #FF4136; }
            .control-btn.live-btn.active { background-color: #FF4136; color: white; animation: pulse 2s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
            .control-panel { width: 300px; margin: 0 auto 20px auto; text-align: center; }
            .live-price-big { text-align: center; font-size: 3rem; color: #fff; margin-bottom: 30px; }
            .flex-container { display: flex; gap: 20px; padding: 0 20px; }
            .chart-wrapper { flex: 3; min-width: 600px; background-color: #1e1e1e; border-radius: 8px; }
            .metrics-container { flex: 1; background-color: #1e1e1e; padding: 20px; border-radius: 8px; height: fit-content; }
            .market-cap-card { background-color: #151a1e; border: 1px solid #2a2e39; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px; }
            .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            .metric-box { background-color: #151a1e; border: 1px solid #2a2e39; border-radius: 8px; padding: 10px; text-align: center; }
            .metric-title { font-size: 0.8rem; color: #888; margin-bottom: 5px; }
            .metric-value { font-size: 1rem; color: #fff; font-weight: bold; }
            .metric-value-large { font-size: 1.5rem; color: #fff; font-weight: bold; }
            .score-bar { height: 6px; background-color: #2a2a2a; border-radius: 3px; margin-top: 10px; position: relative; }
            .score-fill { height: 100%; background-color: #00CC96; border-radius: 3px; width: 98%; }
            .bottom-bar-chart { margin: 20px; background-color: #1e1e1e; padding: 15px; border-radius: 8px; }
            .market-table-container { padding: 20px; }
            .crypto-table { width: 100%; border-collapse: collapse; color: #fff; font-size: 0.9rem; }
            .crypto-table th { text-align: left; padding: 15px; border-bottom: 1px solid #333; color: #888; font-size: 0.8rem; }
            .crypto-table td { padding: 12px; border-bottom: 1px solid #2a2e39; vertical-align: middle; }
            .crypto-table tr:hover { background-color: #1a1f26; }
            .coin-cell { display: flex; align-items: center; gap: 10px; }
            .coin-icon { width: 28px; height: 28px; border-radius: 50%; background-color: #333; object-fit: cover; }
            .coin-symbol { color: #888; font-size: 0.8rem; margin-left: 5px; }
            .positive { color: #00CC96; font-weight: bold; }
            .negative { color: #FF4136; font-weight: bold; }
            .sparkline-cell { width: 120px; padding: 0 !important; }
            .pagination-container { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 20px; }
            .page-btn { background-color: #246BFD; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; cursor: pointer; transition: 0.2s; }
            .page-btn:disabled { background-color: #333; color: #666; cursor: not-allowed; }
            .page-btn:hover:not(:disabled) { background-color: #1b53d6; }
            .page-text { color: white; font-weight: bold; }
            .trending-wrapper { display: flex; gap: 20px; padding: 20px; flex-wrap: wrap; }
            .trending-card { flex: 1; background-color: #1e1e1e; border-radius: 10px; padding: 20px; min-width: 300px; border: 1px solid #333; }
            .trending-header { font-size: 1.5rem; font-weight: bold; margin-bottom: 20px; }
            .trending-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #2a2e39; }
            .rank-badge { width: 20px; text-align: center; color: #888; margin-right: 10px; }
            .trend-price { font-weight: bold; }
            .trend-pct { padding: 2px 8px; border-radius: 4px; font-size: 0.9rem; min-width: 70px; text-align: right; }
            .bg-green { background-color: rgba(0, 204, 150, 0.15); color: #00CC96; }
            .bg-red { background-color: rgba(255, 65, 54, 0.15); color: #FF4136; }
            .news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
            .news-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; overflow: hidden; transition: 0.3s; }
            .news-card:hover { transform: translateY(-5px); border-color: #00CC96; }
            .news-img { width: 100%; height: 160px; object-fit: cover; }
            .news-content { padding: 15px; }
            .news-tag { background-color: #246BFD; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; text-transform: uppercase; }
            .news-title { font-size: 1.1rem; font-weight: bold; margin: 10px 0; line-height: 1.4; color: #eee; }
            .news-meta { display: flex; justify-content: space-between; color: #888; font-size: 0.8rem; margin-top: 10px; }
            .analytics-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; padding: 20px; }
            .analytics-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; padding: 20px; }
            .card-title { color: #eee; font-size: 1.2rem; font-weight: bold; margin-bottom: 15px; display: flex; justify-content: space-between; }
            .status-pill { font-size: 0.9rem; padding: 4px 10px; border-radius: 15px; background-color: #333; color: white; }
            .meter-bar-container { background-color: #2a2a2a; height: 8px; border-radius: 4px; margin: 15px 0; position: relative; }
            .meter-bar-puell { background: linear-gradient(90deg, #00CC96 20%, #444 50%, #FF4136 80%); width: 100%; height: 100%; border-radius: 4px; }
            .meter-bar-top { background: linear-gradient(90deg, #00CC96, #FF4136); width: 100%; height: 100%; border-radius: 4px; }
            .meter-knob { width: 12px; height: 12px; background: white; border-radius: 50%; position: absolute; top: -2px; box-shadow: 0 0 5px rgba(255,255,255,0.5); transition: left 0.5s; }
            .meter-labels { display: flex; justify-content: space-between; color: #888; font-size: 0.8rem; }
            .big-stat { font-size: 2rem; font-weight: bold; color: white; margin-bottom: 5px; }
            .valuation-bar-container { margin-top: 20px; }
            .val-label { display: flex; justify-content: space-between; color: #888; font-size: 0.9rem; margin-bottom: 5px; }
            .val-bar { height: 10px; background: linear-gradient(90deg, #00CC96, #FF4136); border-radius: 5px; position: relative; }
            .val-indicator { width: 4px; height: 16px; background-color: white; position: absolute; top: -3px; border-radius: 2px; box-shadow: 0 0 5px rgba(0,0,0,0.5); transition: left 0.5s; }
            .dex-scroll-container { display: flex; gap: 20px; overflow-x: auto; padding-bottom: 10px; scrollbar-width: thin; scrollbar-color: #333 #121212; }
            .dex-scroll-container::-webkit-scrollbar { height: 8px; }
            .dex-scroll-container::-webkit-scrollbar-track { background: #121212; }
            .dex-scroll-container::-webkit-scrollbar-thumb { background-color: #333; border-radius: 4px; }
            .dex-card { min-width: 320px; background: #151a1e; border-radius: 12px; padding: 15px; border: 1px solid #2a2e39; }
            .dex-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-size: 1.1rem; font-weight: bold; }
            .dex-header span:first-child { color: #fff; }
            .dex-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #222; font-size: 0.9rem; }
            .dex-row:last-child { border-bottom: none; }
            .dex-col-left { display: flex; align-items: center; gap: 8px; width: 40%; }
            .dex-rank { color: #666; font-size: 0.8rem; width: 15px; }
            .dex-icon { width: 24px; height: 24px; border-radius: 50%; background: #333; }
            .dex-name { color: #eee; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .dex-col-mid { width: 30%; text-align: right; font-size: 0.75rem; color: #888; line-height: 1.3; }
            .dex-col-right { width: 30%; text-align: right; }
            .dex-price { font-weight: bold; color: #fff; }
            .dex-change-up { color: #FF4136; font-size: 0.8rem; }
            .dex-change-down { color: #00CC96; font-size: 0.8rem; }
            .spot-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; padding: 20px; }
            .spot-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; padding: 20px; }
            .mkt-cap-main { font-size: 3.5rem; font-weight: bold; color: #fff; }
            .mkt-cap-change { font-size: 1.2rem; margin-left: 10px; font-weight: bold; }
            .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
            .stat-card { background: #2a2e39; padding: 15px; border-radius: 8px; text-align: center; }
            .stat-label { color: #888; font-size: 0.9rem; }
            .stat-val { color: #fff; font-size: 1.1rem; font-weight: bold; margin-top: 5px; }
            .presale-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
            .presale-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 20px; position: relative; overflow: hidden; }
            .presale-badge { position: absolute; top: 15px; right: 15px; background: #246BFD; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
            .presale-header { display: flex; align-items: center; gap: 15px; margin-bottom: 15px; }
            .presale-icon { width: 50px; height: 50px; border-radius: 50%; background: #333; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: bold; color: #fff; border: 2px solid #444; }
            .presale-title { font-size: 1.3rem; font-weight: bold; color: white; }
            .presale-symbol { color: #888; font-size: 0.9rem; }
            .presale-desc { color: #aaa; font-size: 0.9rem; margin-bottom: 15px; line-height: 1.4; height: 40px; overflow: hidden; }
            .progress-container { margin: 15px 0; }
            .progress-bar-bg { background: #333; height: 8px; border-radius: 4px; overflow: hidden; }
            .progress-bar-fill { height: 100%; background: linear-gradient(90deg, #246BFD, #00CC96); border-radius: 4px; }
            .progress-labels { display: flex; justify-content: space-between; color: #ccc; font-size: 0.8rem; margin-top: 5px; }
            .countdown { background: #2a2e39; padding: 10px; border-radius: 6px; text-align: center; color: #00CC96; font-weight: bold; margin-bottom: 15px; }
            .presale-btn { width: 100%; background: #246BFD; border: none; color: white; padding: 10px; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; }
            .presale-btn:hover { background: #1b53d6; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''

# --- MAIN DASHBOARD LAYOUT FUNCTION ---
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
            
            dcc.Tab(label='Analysis', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(className='control-panel', style={'marginTop': '20px'}, children=[
                    html.P("Select Asset for Analysis:", style={'marginBottom': '5px'}),
                    dcc.Dropdown(id='analysis-coin-dropdown', options=DROPDOWN_OPTIONS, value=DEFAULT_SYMBOL, clearable=False, style={'backgroundColor': '#ffffff', 'color': '#000000', 'borderRadius': '5px'}),
                ]),
                html.Div(className='analytics-grid', children=[
                    html.Div([
                        html.Div(className='analytics-card', style={'marginBottom': '20px'}, children=[html.Div([html.Span("Pi Cycle Top Indicator"), html.Span("111DMA vs 350DMA x2", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title'), dcc.Graph(id='pi-cycle-chart', style={'height': '300px'})]),
                        html.Div(className='analytics-card', style={'marginBottom': '20px'}, children=[html.Div([html.Span("Rainbow Price Chart"), html.Span("Long Term Trend", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title'), dcc.Graph(id='rainbow-chart', style={'height': '300px'})]),
                        html.Div(className='analytics-card', children=[html.Div([html.Span("Puell Multiple Chart"), html.Span("Buy/Sell Zones", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title'), dcc.Graph(id='puell-chart', style={'height': '300px'})])
                    ]),
                    html.Div([
                        html.Div(className='analytics-card', style={'marginBottom': '20px', 'textAlign': 'center'}, children=[html.Div("Puell Multiple Status ⓘ", className='card-title'), html.Div(id='puell-val-text', className='big-stat'), html.Div(className='meter-bar-container', children=[html.Div(className='meter-bar-puell'), html.Div(id='puell-knob', className='meter-knob')]), html.Div(className='meter-labels', children=[html.Span("Undervalued"), html.Span("Overvalued")])]),
                        html.Div(className='analytics-card', style={'marginBottom': '20px', 'textAlign': 'center'}, children=[html.Div("Crypto Market Cycle Top Indicators ⓘ", className='card-title'), html.Div(id='top-val-text', className='big-stat'), html.Div(className='meter-bar-container', children=[html.Div(className='meter-bar-top'), html.Div(id='top-knob', className='meter-knob')]), html.Div(className='meter-labels', children=[html.Span("Hold"), html.Span("Sell")])]),
                        html.Div(className='analytics-card', style={'marginBottom': '20px'}, children=[html.Div([html.Span("Valuation Index"), html.Span(id='val-score', className='status-pill')], className='card-title'), html.Div(className='valuation-bar-container', children=[html.Div(className='val-label', children=[html.Span("Undervalued (Buy)"), html.Span("Overvalued (Sell)")]), html.Div(className='val-bar', children=[html.Div(id='val-indicator', className='val-indicator', style={'left': '50%'})])])]),
                        html.Div(className='analytics-card', style={'textAlign': 'center'}, children=[html.Div("Market Cycle Status", className='card-title', style={'justifyContent': 'center'}), html.H2(id='cycle-status-text', style={'color': '#fff', 'margin': '10px 0'}), html.Div(id='cycle-desc', style={'color': '#888', 'fontSize': '0.9rem'})]),
                    ])
                ])
            ]),

            dcc.Tab(label='Spot Market', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(className='spot-grid', children=[
                    html.Div([
                        html.Div(className='analytics-card', style={'marginBottom': '20px'}, children=[html.Div([html.Div([html.H3("Crypto Market Cap", style={'color':'#aaa', 'marginBottom':'5px'}), html.Div([html.Span(id='global-mkt-cap', className='mkt-cap-main'), html.Span(id='global-mkt-change', className='mkt-cap-change')])])], style={'display':'flex', 'justifyContent':'space-between'}), dcc.Graph(id='global-mkt-chart', style={'height': '300px'})]),
                        html.Div(className='analytics-card', children=[html.H4("Crypto Spot Volume (24h)", style={'color':'#fff'}), dcc.Graph(id='global-vol-chart', style={'height': '300px'})])
                    ]),
                    html.Div([
                        html.Div(className='analytics-card', style={'marginBottom': '20px'}, children=[html.H4("Market Cap Historical Values", style={'color':'#fff'}), html.Div(className='stat-grid', children=[html.Div(className='stat-card', children=[html.Div("Yesterday", className='stat-label'), html.Div(id='hist-1d', className='stat-val')]), html.Div(className='stat-card', children=[html.Div("Last Week", className='stat-label'), html.Div(id='hist-7d', className='stat-val')]), html.Div(className='stat-card', children=[html.Div("Last Month", className='stat-label'), html.Div(id='hist-30d', className='stat-val')]), html.Div(className='stat-card', children=[html.Div("Last Year", className='stat-label'), html.Div(id='hist-1y', className='stat-val')])]), html.H4("Market Cap Yearly Performance", style={'color':'#fff', 'marginTop':'20px'}), html.Div(className='stat-grid', children=[html.Div(className='stat-card', children=[html.Div("Yearly High", className='stat-label'), html.Div(id='year-high', className='stat-val', style={'color':'#00CC96'})]), html.Div(className='stat-card', children=[html.Div("Yearly Low", className='stat-label'), html.Div(id='year-low', className='stat-val', style={'color':'#FF4136'})])])]),
                        html.Div(className='analytics-card', children=[html.H4("CEX Spot Volume (24h)", style={'color':'#fff'}), dcc.Graph(id='cex-dominance-chart', style={'height': '300px'})])
                    ])
                ])
            ]),

            dcc.Tab(label='Trading View', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'height': '750px', 'padding': '20px'}, children=[html.Iframe(id='tradingview-iframe', style={'width': '100%', 'height': '100%', 'border': 'none'})])]),

            dcc.Tab(label='Markets', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(className='market-table-container', children=[html.H2("Top 100 Cryptocurrencies", style={'color': 'white', 'marginBottom': '20px'}), html.Div(id='markets-table-content', style={'overflowX': 'auto'}, children="Loading Market Data..."), html.Div(className='pagination-container', children=[html.Button("< Previous", id='prev-btn', className='page-btn'), html.Span(id='page-display', className='page-text', children="Page 1 of 10"), html.Button("Next >", id='next-btn', className='page-btn')])])]),

            dcc.Tab(label='DexScan Tokens', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'padding': '20px'}, children=[html.H2("DexScan Tokens (Simulated)", style={'color': 'white', 'marginBottom': '20px'}), html.Div(id='dexscan-content', className='dex-scroll-container', children="Loading DexScan...")])]),

            dcc.Tab(label='Upcoming', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(style={'padding': '20px'}, children=[
                    html.H2("🚀 Best Upcoming Crypto Presales (2025)", style={'color': '#00CC96', 'marginBottom': '20px', 'textAlign': 'center'}),
                    html.Div(className='presale-grid', children=[
                        html.Div(className='presale-card', children=[
                            html.Div(p['category'], className='presale-badge'),
                            html.Div(className='presale-header', children=[
                                html.Div(p['symbol'][:2], className='presale-icon'),
                                html.Div([html.Div(p['name'], className='presale-title'), html.Div(p['symbol'], className='presale-symbol')])
                            ]),
                            html.P(p['desc'], className='presale-desc'),
                            html.Div(className='progress-container', children=[
                                html.Div(className='progress-labels', children=[html.Span(f"Raised: {p['raised']}"), html.Span(f"Target: {p['target']}")]) ,
                                html.Div(className='progress-bar-bg', children=[html.Div(className='progress-bar-fill', style={'width': p['raised']})])
                            ]),
                            html.Div(f"Launch Price: {p['price']}", className='countdown'),
                            html.Button("Join Presale (Demo)", className='presale-btn')
                        ]) for p in UPCOMING_PROJECTS
                    ])
                ])
            ]),

            dcc.Tab(label='Trending', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='trending-content', className='trending-wrapper', children="Loading Trending Data...")]),

            dcc.Tab(label='News', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='news-content', className='news-grid', children="Loading Latest Crypto News...")])
        ]),
        
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
    dcc.Store(id='login-state-store', data=False),
    # FIX: get_welcome_layout is now defined above.
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
    # print(f"DIAG: Running SLOW Ticker/Bar Chart update (Interval: {n})")
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
            # print("DIAG: Serving 1m chart data from cache.")
            return cache_data # No need to refetch
        
        if tf_data['tf'] != '1m' and cache_data['df_json'] is not None:
            # print("DIAG: Serving historical chart data from cache.")
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
     Output('chart-title', 'children'),
     Output('tradingview-iframe', 'srcDoc')],
    [Input('interval-component', 'n_intervals'),
     Input('coin-select-dropdown', 'value'),
     Input('timeframe-store', 'data'),
     Input('ws-data-store', 'data'),
     Input('ticker-data-store', 'data'), # Slow data for metrics
     Input('chart-data-cache', 'data')] # Cached historical data
)
def update_overview_fast(n, selected_symbol, tf_data, ws_data, ticker_data, cache_data):
    
    # print(f"DIAG: Running FAST Chart Update (Interval: {n}). Cache status: {cache_data['df_json'] is not None}")
    tv_html = get_tradingview_html(selected_symbol)
    
    if not selected_symbol or cache_data['df_json'] is None: 
        return go.Figure(), "Loading...", "Loading Metrics", "Loading Chart", tv_html
        
    # Load DataFrame from cached JSON
    try:
        df = pd.read_json(StringIO(cache_data['df_json']), orient='split')
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    except:
        return go.Figure(), "N/A", "Data Error", "Chart Error", tv_html

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
        html.Div(className='market-cap-card', children=[
            html.Div("Market Cap ⓘ", className='metric-title'),
            html.Div(format_compact(market_cap), className='metric-value-large'),
            html.Div(f"{pct_change:+.2f}%", style={'color': color, 'fontSize': '0.9rem', 'marginTop': '5px'})
        ]),
        html.Div(className='metric-grid', children=[
            html.Div(className='metric-box', children=[html.Div("Volume (24h)", className='metric-title'), html.Div(format_compact(volume), className='metric-value')]),
            html.Div(className='metric-box', children=[html.Div("FDV", className='metric-title'), html.Div(format_compact(fdv), className='metric-value')]),
            html.Div(className='metric-box', children=[html.Div("Vol/Mkt Cap", className='metric-title'), html.Div(f"{(volume/market_cap*100):.2f}%" if market_cap > 0 else "N/A", className='metric-value')]),
            html.Div(className='metric-box', children=[html.Div("Total Supply", className='metric-title'), html.Div(f"{format_compact(supply['supply']).replace('₹ ', '')} {supply['symbol']}", className='metric-value')]),
            html.Div(className='metric-box', children=[html.Div("Max Supply", className='metric-title'), html.Div(f"{format_compact(supply['max']).replace('₹ ', '')} {supply['symbol']}" if supply['max'] else "∞", className='metric-value')]),
            html.Div(className='metric-box', children=[html.Div("Circulating", className='metric-title'), html.Div(f"{format_compact(supply['supply']).replace('₹ ', '')}", className='metric-value')])
        ]),
        html.Div(className='market-cap-card', style={'marginTop': '15px', 'padding': '10px'}, children=[
            html.Div(style={'display': 'flex', 'justifyContent': 'space-between'}, children=[
                html.Span("Profile Score", style={'color': '#888'}),
                html.Span("100%", style={'color': '#00CC96', 'fontWeight': 'bold'})
            ]),
            html.Div(className='score-bar', children=[html.Div(className='score-fill')])
        ])
    ]
    
    # 5. RENDER CHART
    fig_candle = go.Figure(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00CC96', decreasing_line_color='#FF4136', name='Price'))
    df.loc[:, 'SMA'] = df['close'].rolling(5).mean() 
    fig_candle.add_trace(go.Scatter(x=df['timestamp'], y=df['SMA'], line=dict(color='white', width=1), name='SMA (Trend)'))
    fig_candle.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=0, r=40, t=10, b=20), yaxis=dict(gridcolor='#333'), xaxis=dict(gridcolor='#333'), hovermode='x unified', hoverlabel=dict(bgcolor="#1e1e1e", font_size=12, font_color="white", bordercolor="#333"))
    
    price_html = html.Span(f"Live Price: {format_currency(latest_price)}", style={'color': color})
    
    title_suffix = "LIVE VIEW (Last 50 Mins)" if tf_data['tf'] == '1m' else "Past 24 Hours"
    return fig_candle, price_html, metrics_html, f"{full_name} Analysis - {title_suffix}", tv_html

@app.callback(
    Output('page-content', 'children'),
    Output('login-state-store', 'data'),
    Input('login-btn-main', 'n_clicks'),
    State('login-state-store', 'data'),
    prevent_initial_call=True
)
def login_success(n_clicks, current_state):
    if n_clicks and n_clicks > 0:
        return get_dashboard_layout(), True
    return dash.no_update, dash.no_update

# --- MODAL CALLBACKS (FIXED & UPDATED) ---
@app.callback(
    Output('modal-container', 'children'),
    [Input('about-link-btn', 'n_clicks'), 
     Input('contact-link-btn', 'n_clicks'),
     Input({'type': 'close-modal', 'index': 0}, 'n_clicks')], # Pattern matching input for dynamic close button
    prevent_initial_call=True
)
def manage_modal(about_click, contact_click, close_click):
    ctx_id = ctx.triggered_id
    
    # अगर क्लिक बाहर से आया है या क्लोज बटन दबाया गया है
    if not ctx_id or (isinstance(ctx_id, dict) and ctx_id['type'] == 'close-modal'):
        return None

    content = None
    
    # 1. ABOUT PAGE CONTENT
    if ctx_id == 'about-link-btn':
        content = html.Div(className='about-text', children=[
            html.H2("About Crypto Master", style={'color': '#00CC96', 'marginBottom': '20px'}),
            html.P("Crypto Master Terminal is a professional-grade platform designed for real-time cryptocurrency market analysis.", style={'fontSize': '1.1rem'}),
            html.P("Our mission is to empower traders with institutional-level data, live charting, and advanced indicators.", style={'color': '#aaa'}),
            html.Div("Developed by Raghav Ahir Yaduvanshi", style={'marginTop': '20px', 'fontSize': '0.9rem', 'color': '#00CC96'})
        ])

    # 2. CONTACT PAGE CONTENT (With Your Details)
    elif ctx_id == 'contact-link-btn':
        # आपकी फोटो का URL (GitHub raw link)
        photo_url = 'https://raw.githubusercontent.com/rahir19/host-image/main/raghav_pic.jpeg' 
        
        content = html.Div(className='contact-info-box', children=[
            # Profile Picture in Circle
            html.Img(src=photo_url, className='profile-pic'),
            
            # Name
            html.H3("Raghav Ahir Yaduvanshi", style={'color': 'white', 'marginBottom': '5px'}),
            html.Div("Full Stack Developer", style={'color': '#00CC96', 'fontSize': '0.9rem', 'marginBottom': '20px'}),
            
            # Mobile Number
            html.Div(className='contact-item', children=[
                html.Span("📞 Mobile:", className='contact-label', style={'color': '#00CC96', 'marginRight': '10px'}),
                html.Span("+91 6266649445", className='contact-val')
            ]),
            
            # LinkedIn
            html.Div(className='contact-item', children=[
                 html.Span("🔗 LinkedIn:", className='contact-label', style={'color': '#00CC96', 'marginRight': '10px'}),
                 html.A("View Profile", href="https://www.linkedin.com/in/raghav-ahir-117b8b357/", target="_blank", className='contact-link')
            ]),
            
            # GitHub
            html.Div(className='contact-item', children=[
                 html.Span("💻 GitHub:", className='contact-label', style={'color': '#00CC96', 'marginRight': '10px'}),
                 html.A("rahir19", href="https://github.com/rahir19", target="_blank", className='contact-link')
             ]),
        ])

    # Show Modal with Close Button (X)
    if content:
        return html.Div(className='modal-overlay', children=[
            html.Div(className='modal-content', children=[
                 # Close Button with Pattern Matching ID
                 html.Span("×", id={'type': 'close-modal', 'index': 0}, className='modal-close'),
                 content
            ])
        ])
    return None

@app.callback(
    [Output('timeframe-store', 'data'),
     Output({'type': 'tf-btn', 'index': ALL}, 'className'),
     Output('interval-component', 'interval', allow_duplicate=True)],
    [Input({'type': 'tf-btn', 'index': ALL}, 'n_clicks')],
    [State('timeframe-store', 'data')],
    prevent_initial_call=True
)
def update_controls(n_clicks, current_tf_data):
    ctx_msg = ctx.triggered_id
    tf_data = current_tf_data
    interval_speed = 60000 
    
    if ctx_msg and ctx_msg['type'] == 'tf-btn':
        selected_tf = ctx_msg['index']
        if selected_tf == 'LIVE': tf_data = {'tf': '1m', 'limit': 50}; interval_speed = 500
        elif selected_tf == '24H': tf_data = {'tf': '15m', 'limit': 96}; interval_speed = 60000
        elif selected_tf == '7D': tf_data = {'tf': '1h', 'limit': 168}; interval_speed = 60000
        elif selected_tf == '1M': tf_data = {'tf': '4h', 'limit': 180}; interval_speed = 60000
        elif selected_tf == '1Y': tf_data = {'tf': '1d', 'limit': 365}; interval_speed = 60000
        elif selected_tf == '5Y': tf_data = {'tf': '1w', 'limit': 260}; interval_speed = 60000

    active_tf_label = 'LIVE'
    if tf_data['limit'] == 96: active_tf_label = '24H'
    elif tf_data['limit'] == 168: active_tf_label = '7D'
    elif tf_data['limit'] == 180: active_tf_label = '1M'
    elif tf_data['limit'] == 365: active_tf_label = '1Y'
    elif tf_data['limit'] == 260: active_tf_label = '5Y'
    
    styles = ['control-btn live-btn active' if i['id']['index'] == 'LIVE' and active_tf_label == 'LIVE' else ('control-btn active' if i['id']['index'] == active_tf_label else ('control-btn live-btn' if i['id']['index'] == 'LIVE' else 'control-btn')) for i in ctx.inputs_list[0]]
    
    return tf_data, styles, interval_speed

# --- MISSING CALLBACKS ADDED BELOW ---

@app.callback(
    [Output('global-mkt-cap', 'children'), Output('global-mkt-change', 'children'), Output('global-mkt-chart', 'figure'), Output('global-vol-chart', 'figure'), Output('cex-dominance-chart', 'figure'), Output('hist-1d', 'children'), Output('hist-7d', 'children'), Output('hist-30d', 'children'), Output('hist-1y', 'children'), Output('year-high', 'children'), Output('year-low', 'children')],
    Input('market-interval', 'n_intervals')
)
def update_spot_market(n):
    data = generate_global_market_data()
    if not data: return "Loading...", "", go.Figure(), go.Figure(), go.Figure(), "-", "-", "-", "-", "-", "-"
    times, mkt_caps, volumes = data; current_cap = mkt_caps.iloc[-1]; prev_cap = mkt_caps.iloc[-2]; change = ((current_cap - prev_cap) / prev_cap) * 100; color = '#00CC96' if change >= 0 else '#FF4136'
    fig_cap = go.Figure(go.Scatter(x=times, y=mkt_caps, mode='lines', fill='tozeroy', line=dict(color='#00CC96', width=2), fillcolor='rgba(0, 204, 150, 0.1)')); fig_cap.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=10, t=10, b=30), height=300)
    fig_vol = go.Figure(go.Scatter(x=times, y=volumes, mode='lines', line=dict(color='#00CC96', width=2))); fig_vol.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=10, t=10, b=30), height=300)
    x_vals = times[-90:]; y_binance = np.random.normal(50, 2, 90); y_coinbase = np.random.normal(15, 1, 90); y_dex = np.random.normal(20, 3, 90); y_others = 100 - (y_binance + y_coinbase + y_dex)
    fig_dom = go.Figure(); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_binance, stackgroup='one', name='Binance', line=dict(width=0))); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_coinbase, stackgroup='one', name='Coinbase', line=dict(width=0))); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_dex, stackgroup='one', name='DEXs', line=dict(width=0))); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_others, stackgroup='one', name='Others', line=dict(width=0))); fig_dom.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=10, t=10, b=30), height=300)
    return format_compact(current_cap), html.Span(f"{change:+.2f}% (24h)", style={'color': color}), fig_cap, fig_vol, fig_dom, format_compact(mkt_caps.iloc[-2]), format_compact(mkt_caps.iloc[-8]), format_compact(mkt_caps.iloc[-31]), format_compact(mkt_caps.iloc[0]), format_compact(mkt_caps.max()), format_compact(mkt_caps.min())

@app.callback([Output('pi-cycle-chart', 'figure'), Output('rainbow-chart', 'figure'), Output('puell-chart', 'figure'), Output('puell-val-text', 'children'), Output('puell-knob', 'style'), Output('top-val-text', 'children'), Output('top-knob', 'style'), Output('val-indicator', 'style'), Output('val-score', 'children'), Output('cycle-status-text', 'children'), Output('cycle-desc', 'children')], [Input('market-interval', 'n_intervals'), Input('analysis-coin-dropdown', 'value')])
def update_analytics(n, selected_symbol):
    if not selected_symbol: return go.Figure(), go.Figure(), go.Figure(), "", {}, "", {}, {}, "", "", ""
    df_json = fetch_chart_data(selected_symbol, '1d', 1000) # Reduced limit to 1000 to avoid timeouts
    if not df_json: return go.Figure(), go.Figure(), go.Figure(), "N/A", {}, "N/A", {}, {}, "N/A", "No Data", "Select BTC/ETH"
    
    df = pd.read_json(StringIO(df_json), orient='split')
    # Reconvert timestamp after JSON serialization
    # FIX: Check if already tz-aware before localizing
    if df['timestamp'].dt.tz is None:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')

    df, current_puell, puell_meter_val, top_score = calculate_advanced_metrics(df)
    
    fig_pi = go.Figure(); fig_pi.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='Price', line=dict(color='white', width=1))); fig_pi.add_trace(go.Scatter(x=df['timestamp'], y=df['111DMA'], mode='lines', name='111 DMA', line=dict(color='#00CC96', width=2))); fig_pi.add_trace(go.Scatter(x=df['timestamp'], y=df['350DMA'], mode='lines', name='350 DMA x2', line=dict(color='#FF4136', width=2))); fig_pi.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=30, r=10, t=30, b=30), legend=dict(orientation="h", y=1.1))
    fig_rain = go.Figure(); base = df['Rainbow_Base']; colors = ['purple', 'blue', 'green', 'yellow', 'orange', 'red']; multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75]
    for i, mult in enumerate(multipliers): fig_rain.add_trace(go.Scatter(x=df['timestamp'], y=base*mult, mode='lines', line=dict(width=0), showlegend=False, fill='tonexty' if i>0 else 'none', fillcolor=colors[i]))
    fig_rain.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='Price', line=dict(color='white', width=2))); fig_rain.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=30, r=10, t=30, b=30), showlegend=False, yaxis_type="log")
    fig_puell = go.Figure(); fig_puell.add_hrect(y0=4, y1=10, fillcolor="rgba(255, 65, 54, 0.2)", line_width=0); fig_puell.add_hrect(y0=0, y1=0.5, fillcolor="rgba(0, 204, 150, 0.2)", line_width=0); fig_puell.add_trace(go.Scatter(x=df['timestamp'], y=df['Puell'], mode='lines', name='Puell Multiple', line=dict(color='#246BFD', width=2))); fig_puell.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=30, r=10, t=30, b=30), yaxis_title="Multiple")
    dma_200 = df['close'].rolling(window=200).mean().iloc[-1]; val_score = 50
    if dma_200 > 0: val_score = min(max((df['close'].iloc[-1] / dma_200 - 0.5) / 1.9 * 100, 0), 100)
    status = "Top Heavy (Sell)" if val_score > 80 else ("Bottom (Buy)" if val_score < 20 else "Neutral")
    desc = "Market is overheated." if val_score > 80 else ("Market is in accumulation zone." if val_score < 20 else "Market is currently in a neutral zone.")
    return fig_pi, fig_rain, fig_puell, f"{current_puell:.2f}", {'left': f'{puell_meter_val}%'}, f"{top_score:.1f}%", {'left': f'{top_score}%'}, {'left': f'{val_score}%'}, f"{val_score:.0f}/100", status, desc

@app.callback([Output('markets-table-content', 'children'), Output('trending-content', 'children'), Output('news-content', 'children'), Output('dexscan-content', 'children'), Output('current-page-store', 'data', allow_duplicate=True), Output('page-display', 'children'), Output('prev-btn', 'disabled'), Output('next-btn', 'disabled')], [Input('market-interval', 'n_intervals'), Input('prev-btn', 'n_clicks'), Input('next-btn', 'n_clicks')], [State('current-page-store', 'data')], prevent_initial_call=True)
def update_market_trending_news_dex(n, prev_clicks, next_clicks, current_page):
    market_data = fetch_market_data()
    ctx_id = ctx.triggered_id
    if ctx_id == 'prev-btn' and current_page > 1: current_page -= 1
    if ctx_id == 'next-btn' and current_page < 10: current_page += 1
    if not market_data: return html.Div("Loading..."), html.Div("Loading..."), html.Div("Loading..."), html.Div("Loading..."), current_page, f"Page {current_page} of 10", True, True
    dex_cards = []
    for cat, coins in DEX_CATEGORIES.items():
        rows = []
        for i, sym in enumerate(coins):
            try:
                coin_data = next((c for c in market_data if c['symbol'] == sym), None)
                if not coin_data: continue
                vol = coin_data['volume'] * random.uniform(0.1, 0.5); fdv = coin_data['mkt_cap'] * random.uniform(0.8, 1.2); price = coin_data['price']; change = coin_data['change_24h']
                rows.append(html.Div(className='dex-row', children=[html.Div(className='dex-col-left', children=[html.Div(f"{i+1}", className='dex-rank'), html.Img(src=get_icon_url(sym), className='dex-icon'), html.Div(coin_data['name'], className='dex-name')]), html.Div(className='dex-col-mid', children=[html.Div(f"Vol {format_compact(vol)}"), html.Div(f"FDV {format_compact(fdv)}")]), html.Div(className='dex-col-right', children=[html.Div(format_currency(price), className='dex-price'), html.Div(f"{change:.2f}%", className='dex-change-down' if change >=0 else 'dex-change-up')])]))
            except: continue
        if rows: dex_cards.append(html.Div(className='dex-card', children=[html.Div(className='dex-header', children=[html.Span(cat), html.Span(">", style={'color': '#666', 'fontSize': '0.9rem'})]), html.Div(rows)]))
    start_idx = (current_page - 1) * 10; end_idx = start_idx + 10; page_data = market_data[start_idx:end_idx]
    header = html.Tr([html.Th("#"), html.Th("Asset"), html.Th("Price"), html.Th("Market Cap"), html.Th("24h Volume"), html.Th("24h %"), html.Th("7d %"), html.Th("Last 7 Days")])
    rows = []
    for coin in page_data:
        col24 = 'positive' if coin['change_24h'] >= 0 else 'negative'; col7d = 'positive' if coin['change_7d'] >= 0 else 'negative'; spark_color = '#00CC96' if coin['change_7d'] >= 0 else '#FF4136'
        fig_spark = go.Figure(go.Scatter(y=coin['history'], mode='lines', line=dict(color=spark_color, width=2), fill='tozeroy', fillcolor=f"rgba({int(spark_color[1:3],16)}, {int(spark_color[3:5],16)}, {int(spark_color[5:7],16)}, 0.1)")); fig_spark.update_layout(template='plotly_dark', height=40, width=120, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        row = html.Tr([html.Td(coin['rank']), html.Td(html.Div(className='coin-cell', children=[html.Img(src=get_icon_url(coin['symbol']), className='coin-icon'), html.Div([html.Div(coin['name'], style={'fontWeight': 'bold'}), html.Div(format_currency(coin['price']), className='trend-price')])])), html.Td(format_currency(coin['price']), style={'fontWeight': 'bold'}), html.Td(format_compact(coin['mkt_cap'])), html.Td(format_compact(coin['volume'])), html.Td(f"{coin['change_24h']:.2f}%", className=col24), html.Td(f"{coin['change_7d']:.2f}%", className=col7d), html.Td(dcc.Graph(figure=fig_spark, config={'staticPlot': True}), className='sparkline-cell')]); rows.append(row)
    table = html.Table([html.Thead(header), html.Tbody(rows)], className='crypto-table')
    gainers = sorted(market_data, key=lambda x: x['change_24h'], reverse=True)[:5]; losers = sorted(market_data, key=lambda x: x['change_24h'])[:5]
    def create_trend_list(items):
        rows = []
        for i, coin in enumerate(items): rows.append(html.Div(className='trending-row', children=[html.Div(className='coin-cell', children=[html.Div(f"{i+1}", className='rank-badge'), html.Img(src=get_icon_url(coin['symbol']), className='coin-icon'), html.Div([html.Div(coin['name'], style={'fontWeight': 'bold'}), html.Div(format_currency(coin['price']), className='trend-price')])]), html.Div(f"{coin['change_24h']:.2f}%", className=f"trend-pct {'bg-green' if coin['change_24h']>=0 else 'bg-red'}")]))
        return rows
    trending_html = [html.Div(className='trending-card', children=[html.Div("🔥 Top Gainers", className='trending-header', style={'color': '#00CC96'}), html.Div(create_trend_list(gainers))]), html.Div(className='trending-card', children=[html.Div("📉 Top Losers", className='trending-header', style={'color': '#FF4136'}), html.Div(create_trend_list(losers))])]
    news_items = generate_crypto_news(); news_cards = []
    for news in news_items: card = html.Div(className='news-card', children=[html.Img(src=news['image'], className='news-img'), html.Div(className='news-content', children=[html.Span(news['source'], className='news-tag'), html.Div(news['title'], className='news-title'), html.P(news['desc'], style={'color':'#aaa', 'fontSize':'0.9rem'}), html.Div(children=[html.Span(news['time']), html.A("Read More", href="#", style={'color':'#00CC96', 'textDecoration':'none'})], className='news-meta')])]); news_cards.append(card)
    return table, trending_html, news_cards, dex_cards, current_page, f"Page {current_page} of 10", (current_page == 1), (current_page == 10)

# --- RUN ---
server = app.server 
if __name__ == '__main__':
    start_websocket_thread() 
    print(f"\n✅ Dashboard Live: http://127.0.0.1:{PORT}\n")
    app.run(debug=False, host='127.0.0.1', port=PORT)
