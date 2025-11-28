import pandas as pd
import plotly.graph_objects as go
import ccxt # Hum ise import rakhenge par use nahi karenge taaki error na aaye
import sys
import time
import locale
import socket
import dash
import json
import random
import numpy as np
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

# --- CONFIGURATION (PRESENTATION MODE) ---
# Hum 'exchange' ko None rakhenge taaki code kabhi bhi connect karne main time waste na kare
exchange = None 

USD_TO_INR_RATE = 84.00

SYMBOL_MAP = {
    'BTC/USDT': 'Bitcoin', 'ETH/USDT': 'Ethereum', 'BNB/USDT': 'Binance Coin',
    'SOL/USDT': 'Solana', 'XRP/USDT': 'XRP', 'DOGE/USDT': 'Dogecoin',
    'ADA/USDT': 'Cardano', 'TRX/USDT': 'TRON', 'AVAX/USDT': 'Avalanche',
    'SHIB/USDT': 'Shiba Inu'
}

# STARTING PRICES (Updated to Current Market for Realism)
BASE_PRICES_USD = {
    'BTC/USDT': 98450,
    'ETH/USDT': 3890,
    'BNB/USDT': 650,
    'SOL/USDT': 145,
    'XRP/USDT': 1.8,
    'DOGE/USDT': 0.42,
    'ADA/USDT': 1.1,
    'TRX/USDT': 0.20,
    'AVAX/USDT': 45,
    'SHIB/USDT': 0.000025
}

COIN_PARAMS = {
    'BTC/USDT': {'supply': 19640000, 'symbol': 'BTC', 'max': 21000000},
    'ETH/USDT': {'supply': 120000000, 'symbol': 'ETH', 'max': None},
    'BNB/USDT': {'supply': 153000000, 'symbol': 'BNB', 'max': 200000000},
    'SOL/USDT': {'supply': 440000000, 'symbol': 'SOL', 'max': None},
    'XRP/USDT': {'supply': 54000000000, 'symbol': 'XRP', 'max': 100000000000},
    'DOGE/USDT': {'supply': 143000000000, 'symbol': 'DOGE', 'max': None},
    'ADA/USDT': {'supply': 35000000000, 'symbol': 'ADA', 'max': 45000000000},
    'TRX/USDT': {'supply': 88000000000, 'symbol': 'TRX', 'max': None},
    'AVAX/USDT': {'supply': 377000000, 'symbol': 'AVAX', 'max': 720000000},
    'SHIB/USDT': {'supply': 589000000000000, 'symbol': 'SHIB', 'max': None}
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
    # Added explicit height/width and loading adjustments
    return f"""
    <!DOCTYPE html>
    <html>
    <head><style>body, html {{ margin: 0; padding: 0; height: 100%; width: 100%; overflow: hidden; background-color: #1e1e1e; }}</style></head>
    <body>
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div id="tradingview_widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{
          "autosize": true,
          "symbol": "{tv_symbol}",
          "interval": "D",
          "timezone": "Asia/Kolkata",
          "theme": "dark",
          "style": "1",
          "locale": "en",
          "toolbar_bg": "#f1f3f6",
          "enable_publishing": false,
          "allow_symbol_change": true,
          "container_id": "tradingview_widget",
          "hide_side_toolbar": false
          }});
          </script>
        </div>
    </body>
    </html>
    """

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

# --- DATA ENGINE (PURE SIMULATION FOR STABILITY) ---
def generate_chart_data(selected_symbol, limit):
    # This function guarantees data is always returned, fixing blank charts
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='T')
    
    # Get base price from our dictionary, or default to 100
    base_usd = BASE_PRICES_USD.get(selected_symbol, 100)
    base_inr = base_usd * USD_TO_INR_RATE
    
    # Create realistic-looking random price movement (Random Walk)
    volatility = base_inr * 0.005 # 0.5% volatility
    changes = np.random.normal(0, volatility, limit)
    price_path = base_inr + np.cumsum(changes)
    
    # Ensure no negative prices
    price_path = np.maximum(price_path, 1.0)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price_path,
        'high': price_path * 1.002,
        'low': price_path * 0.998,
        'close': price_path * (1 + np.random.normal(0, 0.001, limit)),
        'volume': np.random.randint(1000, 50000, limit)
    })
    return df

def generate_market_snapshot():
    data = []
    for i, sym in enumerate(TRACKER_SYMBOLS):
        base_usd = BASE_PRICES_USD.get(sym, 100)
        p_inr = base_usd * USD_TO_INR_RATE
        
        # Add some random variation so it looks "Live"
        p_inr = p_inr * (1 + random.uniform(-0.001, 0.001))
        change = random.uniform(-3, 5)
        
        # Sparkline history
        hist = [p_inr * (1 + random.uniform(-0.02, 0.02)) for _ in range(15)]
        
        data.append({
            'rank': i + 1,
            'symbol': sym,
            'name': SYMBOL_MAP[sym],
            'price': p_inr,
            'change_24h': change,
            'change_7d': change * 1.2,
            'volume': p_inr * random.randint(1000, 5000),
            'mkt_cap': p_inr * COIN_PARAMS.get(sym, {}).get('supply', 1000000),
            'history': hist
        })
    return data

def calculate_advanced_metrics(df):
    if df is None: return None, None, None, None
    df['111DMA'] = df['close'].rolling(window=20).mean() # Shortened for demo display
    df['350DMA'] = df['close'].rolling(window=50).mean() * 1.5
    df['Rainbow_Base'] = df['close'].rolling(window=10).mean()
    df['365DMA'] = df['close'].rolling(window=30).mean()
    
    current_puell = random.uniform(0.5, 3.0)
    puell_meter_val = (current_puell / 4.0) * 100
    top_score = random.uniform(20, 90)
    return df, current_puell, puell_meter_val, top_score

def generate_global_market_data():
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    mkt_cap = np.linspace(2e12, 3e12, 100) * USD_TO_INR_RATE
    volume = np.random.uniform(5e10, 1e11, 100) * USD_TO_INR_RATE
    return dates, pd.Series(mkt_cap), pd.Series(volume)

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
            
            /* --- WELCOME PAGE: GRID BACKGROUND & LAYOUT --- */
            .welcome-container {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background-color: #050a14;
                /* Advanced Grid Pattern */
                background-image: 
                    linear-gradient(rgba(0, 80, 255, 0.05) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 80, 255, 0.05) 1px, transparent 1px);
                background-size: 50px 50px;
                z-index: 2000;
                display: flex; flex-direction: column;
                color: white; overflow: hidden;
            }
            /* Spotlight Effect */
            .welcome-container::after {
                content: ""; position: absolute; top: 50%; left: 50%; width: 100%; height: 100%;
                transform: translate(-50%, -50%);
                background: radial-gradient(circle, rgba(0,80,255,0.15) 0%, transparent 70%);
                pointer-events: none;
            }

            .welcome-nav {
                display: flex; justify-content: space-between; align-items: center;
                padding: 25px 60px; flex-shrink: 0; z-index: 10;
            }
            .welcome-brand { font-size: 1.6rem; font-weight: 900; letter-spacing: 1px; color: white; }
            .welcome-links button { 
                background: transparent; border: 1px solid rgba(255,255,255,0.2); color: white;
                margin-left: 25px; padding: 8px 15px; cursor: pointer;
                font-weight: 600; font-size: 0.9rem; letter-spacing: 0.5px;
                transition: 0.3s;
            }
            .welcome-links button:hover { color: #00CC96; text-shadow: 0 0 10px rgba(0,204,150,0.5); border-color: #00CC96; }
            
            /* SPLIT BODY */
            .welcome-body {
                flex: 1; display: flex; align-items: center; justify-content: space-between;
                padding: 0 100px; gap: 80px; z-index: 10;
            }
            
            /* LEFT: HERO TEXT */
            .hero-section {
                flex: 1; max-width: 650px;
            }
            .hero-title { font-size: 4rem; font-weight: 900; margin-bottom: 20px; line-height: 1.1; color: white; text-shadow: 0 0 20px rgba(0,0,0,0.5); }
            .hero-subtitle { font-size: 1.1rem; color: #8899ac; margin-bottom: 40px; line-height: 1.6; max-width: 500px; }
            
            .login-btn-large {
                background: linear-gradient(90deg, #00CC96, #007bff);
                border: none; color: white; padding: 16px 45px;
                font-size: 1rem; font-weight: bold; border-radius: 50px;
                cursor: pointer; transition: transform 0.3s, box-shadow 0.3s;
                box-shadow: 0 0 20px rgba(0, 204, 150, 0.4);
                letter-spacing: 1px;
            }
            .login-btn-large:hover { transform: translateY(-2px); box-shadow: 0 0 30px rgba(0, 204, 150, 0.6); }

            /* RIGHT: MOBILE MOCKUP (BEZEL-LESS GLOWING) */
            .mobile-mockup-wrapper {
                flex: 1; display: flex; justify-content: center; align-items: center;
                perspective: 1000px;
            }
            .mobile-glow {
                position: absolute; width: 280px; height: 580px;
                background: linear-gradient(45deg, #00CC96, #007bff);
                filter: blur(80px); opacity: 0.5;
                border-radius: 50px; z-index: 0;
            }
            .mobile-frame {
                width: 320px; height: 650px;
                background: #000; border-radius: 40px; /* Bezel-less feel */
                border: 3px solid #333;
                position: relative; overflow: hidden; z-index: 5;
                box-shadow: 0 30px 60px rgba(0,0,0,0.6);
                transform: rotateY(-15deg) rotateX(5deg);
                transition: transform 0.5s ease;
            }
            .mobile-frame:hover { transform: rotateY(0) rotateX(0); }
            
            /* No Notch - Just Full Screen for Modern Look */
            .mobile-screen {
                width: 100%; height: 100%;
                background: #0a0e17;
                overflow: hidden; 
                position: relative;
                padding-top: 20px;
            }
            
            /* ANIMATION & CARDS */
            .scroll-container {
                display: flex; flex-direction: column;
                animation: scrollUp 12s linear infinite;
            }
            @keyframes scrollUp { 0% { transform: translateY(0); } 100% { transform: translateY(-50%); } }
            
            .fake-card {
                background: rgba(30, 35, 45, 0.9); border-radius: 16px;
                margin: 15px; padding: 15px; border: 1px solid rgba(255,255,255,0.05);
            }
            .fake-chart { height: 60px; background: linear-gradient(90deg, #151a21, #1f2530, #151a21); border-radius: 8px; margin-top: 10px; position: relative; }
            .fake-chart::after { content: ''; position: absolute; bottom: 10px; left: 0; width: 100%; height: 2px; background: #00CC96; transform: rotate(-5deg); box-shadow: 0 0 8px #00CC96; }
            .fake-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.85rem; color: white; }
            .txt-green { color: #00CC96; font-weight: bold; } .txt-red { color: #FF4136; font-weight: bold; }

            /* MODAL STYLES (CENTERED OVERLAY) */
            .modal-overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.8); /* Darker dim */
                backdrop-filter: blur(8px); /* Strong blur */
                z-index: 5000;
                display: flex; justify-content: center; align-items: center;
                animation: fadeIn 0.3s ease-out;
            }
            @keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
            
            .modal-content {
                background: #11151a; padding: 40px; border-radius: 20px;
                border: 1px solid #333; text-align: center;
                position: relative; max-width: 450px; width: 90%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.8);
                color: #e0e0e0;
            }
            .modal-close {
                position: absolute; top: 15px; right: 20px; font-size: 2rem; 
                cursor: pointer; color: #666; line-height: 1;
            }
            .modal-close:hover { color: #FF4136; }
            
            .contact-info-box h3 { color: #00CC96; margin-bottom: 25px; font-size: 1.5rem; text-transform: uppercase; letter-spacing: 1px; }
            .contact-item { margin-bottom: 20px; font-size: 1.1rem; border-bottom: 1px solid #222; padding-bottom: 10px; display: flex; justify-content: space-between; }
            .contact-link { color: #007bff; text-decoration: none; font-weight: bold; }
            .contact-link:hover { text-decoration: underline; color: #00CC96; }

            /* DASHBOARD STYLES */
            .navbar { display: flex; justify-content: space-between; align-items: center; background-color: #161a1e; padding: 15px 30px; border-bottom: 1px solid #2a2e39; position: sticky; top: 0; z-index: 1000; }
            .nav-brand { font-size: 1.8rem; font-weight: 900; color: #F0B90B; display: flex; align-items: center; gap: 10px; }
            .nav-controls { display: flex; align-items: center; gap: 15px; }
            .nav-label { color: #888; font-size: 0.9rem; }
            .custom-tabs { border-bottom: 1px solid #333; background: #121212; }
            .custom-tab { background-color: #121212; color: #888; border: none; padding: 15px 25px; font-size: 1rem; cursor: pointer; border-bottom: 2px solid transparent; }
            .custom-tab--selected { background-color: #121212; color: #F0B90B !important; border-bottom: 2px solid #F0B90B; font-weight: bold; }
            .app-footer { text-align: center; padding: 40px 20px; color: #555; font-size: 0.85rem; border-top: 1px solid #222; margin-top: 40px; background-color: #161a1e; }
            
            .control-bar-container { display: flex; justify-content: space-between; align-items: center; background-color: #1e1e1e; padding: 10px 20px; border-radius: 8px 8px 0 0; margin-top: 20px; border-bottom: 1px solid #333; }
            .btn-group { display: flex; background-color: #2a2a2a; border-radius: 6px; padding: 3px; gap: 2px; }
            .control-btn { background-color: transparent; border: none; color: #888; padding: 6px 15px; font-size: 0.9rem; cursor: pointer; border-radius: 4px; font-weight: bold; transition: 0.2s; }
            .control-btn:hover { color: #fff; background-color: #333; }
            .control-btn.active { background-color: #fff; color: #000; }
            .control-btn.live-btn { color: #FF4136; }
            .control-btn.live-btn.active { background-color: #FF4136; color: white; animation: pulse 2s infinite; }
            .control-panel { width: 300px; margin: 0 auto 20px auto; text-align: center; }
            .live-price-big { text-align: center; font-size: 3rem; color: #fff; margin-bottom: 30px; }
            .flex-container { display: flex; gap: 20px; padding: 0 20px; }
            .chart-wrapper { flex: 3; min-width: 600px; background-color: #1e1e1e; border-radius: 8px; }
            .metrics-container { flex: 1; background-color: #1e1e1e; padding: 20px; border-radius: 8px; height: fit-content; }
            .market-cap-card, .metric-box { background-color: #151a1e; border: 1px solid #2a2e39; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 10px; }
            .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            .metric-value-large { font-size: 1.5rem; color: #fff; font-weight: bold; }
            .score-bar { height: 6px; background-color: #2a2a2a; border-radius: 3px; margin-top: 10px; position: relative; }
            .score-fill { height: 100%; background-color: #00CC96; border-radius: 3px; width: 98%; }
            .bottom-bar-chart { margin: 20px; background-color: #1e1e1e; padding: 15px; border-radius: 8px; }
            .market-table-container { padding: 20px; }
            .crypto-table { width: 100%; border-collapse: collapse; color: #fff; font-size: 0.9rem; }
            .crypto-table th { text-align: left; padding: 15px; border-bottom: 1px solid #333; color: #888; font-size: 0.8rem; }
            .crypto-table td { padding: 12px; border-bottom: 1px solid #2a2e39; }
            .coin-cell { display: flex; align-items: center; gap: 10px; }
            .coin-icon { width: 28px; height: 28px; border-radius: 50%; background-color: #333; }
            .positive { color: #00CC96; font-weight: bold; } .negative { color: #FF4136; font-weight: bold; }
            .sparkline-cell { width: 120px; padding: 0 !important; }
            .pagination-container { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 20px; }
            .page-btn { background-color: #246BFD; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; cursor: pointer; transition: 0.2s; }
            .page-btn:hover:not(:disabled) { background-color: #1b53d6; }
            .page-text { color: white; font-weight: bold; }
            .trending-wrapper { display: flex; gap: 20px; padding: 20px; flex-wrap: wrap; }
            .trending-card { flex: 1; background-color: #1e1e1e; border-radius: 10px; padding: 20px; border: 1px solid #333; }
            .trending-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #2a2e39; }
            .analytics-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; padding: 20px; }
            .analytics-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; padding: 20px; }
            .spot-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; padding: 20px; }
            .spot-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; padding: 20px; }
            .dex-scroll-container { display: flex; gap: 20px; overflow-x: auto; padding-bottom: 10px; }
            .dex-card { min-width: 320px; background: #151a1e; border-radius: 12px; padding: 15px; border: 1px solid #2a2e39; }
            .dex-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #222; font-size: 0.9rem; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''

# --- CONTENT GENERATORS ---
def get_fake_content_cards():
    content = []
    for _ in range(2): 
        content.append(html.Div(className='fake-card', children=[
            html.Div("Market Analysis", style={'color':'#888', 'fontSize':'0.8rem'}),
            html.H4("BTC Breaking Resistance?", style={'margin':'5px 0', 'color':'white'}),
            html.Div(className='fake-chart')
        ]))
        content.append(html.Div(className='fake-card', children=[
            html.Div("Live Rates", style={'color':'#888', 'fontSize':'0.8rem', 'marginBottom':'10px'}),
            html.Div(className='fake-row', children=[html.Div("BTC", style={'fontWeight':'bold'}), html.Span("$98,450", className='txt-green')]),
            html.Div(className='fake-row', children=[html.Div("ETH", style={'fontWeight':'bold'}), html.Span("$3,890", className='txt-green')]),
            html.Div(className='fake-row', children=[html.Div("SOL", style={'fontWeight':'bold'}), html.Span("$145", className='txt-red')])
        ]))
    return content

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
                html.Div(className='mobile-glow'),
                html.Div(className='mobile-frame', children=[
                    html.Div(className='mobile-screen', children=[
                        html.Div(className='scroll-container', children=get_fake_content_cards())
                    ])
                ])
            ])
        ]),
        html.Div(id='modal-container')
    ])

def get_dashboard_layout():
    return html.Div([
        html.Div(className='navbar', children=[
            html.Div(className='nav-brand', children=[html.Span("⚡"), html.Span("CRYPTO MASTER")]),
            html.Div(className='nav-controls', children=[
                html.Span("Quick Select:", className='nav-label'),
                dcc.Dropdown(id='coin-select-dropdown', options=DROPDOWN_OPTIONS, value=DEFAULT_SYMBOL, clearable=False, style={'backgroundColor': '#ffffff', 'color': '#000000', 'borderRadius': '5px', 'width': '200px'})
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
                            html.Div(className='btn-group', children=[html.Button("LIVE", id={'type': 'tf-btn', 'index': 'LIVE'}, className='control-btn live-btn active'), html.Button("24H", id={'type': 'tf-btn', 'index': '24H'}, className='control-btn'), html.Button("7D", id={'type': 'tf-btn', 'index': '7D'}, className='control-btn')])
                        ]),
                        html.Div(style={'padding': '15px'}, children=[html.H3(id='chart-title', style={'borderBottom': '1px solid #333', 'paddingBottom': '10px', 'marginTop': '0'}), dcc.Graph(id='live-candlestick-chart', style={'height': '450px'})])
                    ]),
                    html.Div(className='metrics-container', children=[html.Div(id='key-metrics-panel')])
                ]),
                html.Div(className='bottom-bar-chart', children=[html.H4("Top 10 Crypto Performance (24h)", style={'color': '#DDD'}), dcc.Graph(id='bar-chart-24h', style={'height': '300px'})])
            ]),
            dcc.Tab(label='Analysis', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(className='control-panel', style={'marginTop': '20px'}, children=[html.P("Select Asset:", style={'marginBottom': '5px'}), dcc.Dropdown(id='analysis-coin-dropdown', options=DROPDOWN_OPTIONS, value=DEFAULT_SYMBOL, clearable=False, style={'backgroundColor': '#ffffff', 'color': '#000000', 'borderRadius': '5px'})]),
                html.Div(className='analytics-grid', children=[
                    html.Div([html.Div(className='analytics-card', style={'marginBottom': '20px'}, children=[html.Div([html.Span("Pi Cycle Top Indicator"), html.Span("111DMA vs 350DMA x2", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title'), dcc.Graph(id='pi-cycle-chart', style={'height': '300px'})]), html.Div(className='analytics-card', children=[html.Div([html.Span("Rainbow Price Chart"), html.Span("Long Term Trend", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title'), dcc.Graph(id='rainbow-chart', style={'height': '300px'})])]),
                    html.Div([html.Div(className='analytics-card', style={'marginBottom': '20px', 'textAlign': 'center'}, children=[html.Div("Puell Multiple Status ⓘ", className='card-title'), html.Div(id='puell-val-text', className='big-stat'), html.Div(className='meter-bar-container', children=[html.Div(className='meter-bar-puell'), html.Div(id='puell-knob', className='meter-knob')]), html.Div(className='meter-labels', children=[html.Span("Undervalued"), html.Span("Overvalued")])]), html.Div(className='analytics-card', style={'textAlign': 'center'}, children=[html.Div("Market Cycle Status", className='card-title', style={'justifyContent': 'center'}), html.H2(id='cycle-status-text', style={'color': '#fff', 'margin': '10px 0'}), html.Div(id='cycle-desc', style={'color': '#888', 'fontSize': '0.9rem'})])])
                ])
            ]),
            dcc.Tab(label='Spot Market', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(className='spot-grid', children=[html.Div([html.Div(className='analytics-card', children=[html.H3("Crypto Market Cap", style={'color':'#aaa'}), html.Div([html.Span(id='global-mkt-cap', className='mkt-cap-main'), html.Span(id='global-mkt-change', className='mkt-cap-change')]), dcc.Graph(id='global-mkt-chart', style={'height': '300px'})])]), html.Div([html.Div(className='analytics-card', children=[html.H4("Crypto Spot Volume (24h)", style={'color':'#fff'}), dcc.Graph(id='global-vol-chart', style={'height': '300px'})])])])]),
            dcc.Tab(label='Trading View', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'height': '750px', 'padding': '20px'}, children=[html.Iframe(id='tradingview-iframe', style={'width': '100%', 'height': '100%', 'border': 'none'})])]),
            dcc.Tab(label='Markets', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(className='market-table-container', children=[html.H2("Top 100 Cryptocurrencies", style={'color': 'white', 'marginBottom': '20px'}), html.Div(id='markets-table-content', style={'overflowX': 'auto'}, children="Loading Market Data..."), html.Div(className='pagination-container', children=[html.Button("< Previous", id='prev-btn', className='page-btn'), html.Span(id='page-display', className='page-text', children="Page 1 of 10"), html.Button("Next >", id='next-btn', className='page-btn')])])]),
            dcc.Tab(label='DexScan Tokens', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'padding': '20px'}, children=[html.H2("DexScan Tokens (Simulated)", style={'color': 'white', 'marginBottom': '20px'}), html.Div(id='dexscan-content', className='dex-scroll-container', children="Loading DexScan...")])]),
            dcc.Tab(label='Upcoming', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'padding': '20px'}, children=[html.H2("🚀 Best Upcoming Crypto Presales (2025)", style={'color': '#00CC96', 'marginBottom': '20px', 'textAlign': 'center'}), html.Div(className='presale-grid', children=[html.Div(className='presale-card', children=[html.Div(p['category'], className='presale-badge'), html.Div(className='presale-header', children=[html.Div(p['symbol'][:2], className='presale-icon'), html.Div([html.Div(p['name'], className='presale-title'), html.Div(p['symbol'], className='presale-symbol')])]), html.P(p['desc'], className='presale-desc'), html.Div(className='progress-container', children=[html.Div(className='progress-labels', children=[html.Span(f"Raised: {p['raised']}"), html.Span(f"Target: {p['target']}")]) ,html.Div(className='progress-bar-bg', children=[html.Div(className='progress-bar-fill', style={'width': p['raised']})])]), html.Div(f"Launch Price: {p['price']}", className='countdown'), html.Button("Join Presale (Demo)", className='presale-btn')]) for p in UPCOMING_PROJECTS])])]),
            dcc.Tab(label='Trending', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='trending-content', className='trending-wrapper', children="Loading Trending Data...")]),
            dcc.Tab(label='News', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='news-content', className='news-grid', children="Loading Latest Crypto News...")])
        ]),
        html.Div(className='app-footer', children=[html.Div("© 2025 Crypto Master Terminal. All rights reserved.", className='footer-text'), html.Div("Data provided by Binance & Simulated Feeds for Demo.", style={'color': '#444'})]),
        dcc.Interval(id='interval-component', interval=2000, n_intervals=0),
        dcc.Interval(id='market-interval', interval=10000, n_intervals=0)
    ])

# --- APP LAYOUT ---
app.layout = html.Div([
    dcc.Store(id='login-state-store', data=False),
    html.Div(id='page-content', children=get_welcome_layout())
])

# --- CALLBACKS ---
@app.callback(
    Output('page-content', 'children'),
    Input('login-btn-main', 'n_clicks'),
    prevent_initial_call=True
)
def login_success(n_clicks):
    if n_clicks and n_clicks > 0: return get_dashboard_layout()
    return dash.no_update

# UNIFIED MODAL HANDLING
@app.callback(
    Output('modal-container', 'children'),
    [Input('about-link-btn', 'n_clicks'), Input('contact-link-btn', 'n_clicks'), Input({'type': 'close-modal', 'index': 'btn'}, 'n_clicks')],
    prevent_initial_call=True
)
def manage_modals(about_click, contact_click, close_click):
    ctx_id = ctx.triggered_id
    
    # Close Logic (If triggered by close button)
    if ctx_id and isinstance(ctx_id, dict) and ctx_id.get('type') == 'close-modal':
        return None

    # Open Logic
    content = None
    if ctx_id == 'about-link-btn':
        content = html.Div([
            html.H3("About Us", style={'color': '#00CC96'}),
            html.P("Crypto Master Terminal is a professional-grade platform designed for real-time cryptocurrency market analysis. We provide advanced charting, on-chain metrics, and simulated trading environments to help you navigate the crypto space."),
            html.P("Our mission is to empower traders with institutional-level data and insights.")
        ])
    elif ctx_id == 'contact-link-btn':
        content = html.Div(className='contact-info-box', children=[
            html.H3("Contact Information"),
            html.Div(className='contact-item', children=[html.Span("Name"), html.Span("Raghav Ahir Yaduvanshi", style={'fontWeight':'bold'})]),
            html.Div(className='contact-item', children=[html.Span("Phone"), html.Span("6266649445", style={'fontWeight':'bold'})]),
             html.Div(className='contact-item', children=[html.Span("GitHub"), html.A("github.com/rahir19", href="https://github.com/rahir19", target="_blank", className='contact-link')]),
            html.Div(className='contact-item', children=[html.Span("LinkedIn"), html.A("View Profile", href="https://www.linkedin.com/in/raghav-ahir-117b8b357/", target="_blank", className='contact-link')])
        ])

    if content:
        return html.Div(className='modal-overlay', children=[
            html.Div(className='modal-content', children=[
                 html.Span("×", id={'type': 'close-modal', 'index': 'btn'}, className='modal-close'),
                 content
            ])
        ])
    return None

# --- DASHBOARD CALLBACKS ---
@app.callback(
    [Output('timeframe-store', 'data'), Output({'type': 'tf-btn', 'index': ALL}, 'className')],
    [Input({'type': 'tf-btn', 'index': ALL}, 'n_clicks')], [State('timeframe-store', 'data')]
)
def update_controls(n_clicks, current_tf_data):
    ctx_msg = ctx.triggered_id
    tf_data = current_tf_data
    if ctx_msg and ctx_msg['type'] == 'tf-btn':
        sel = ctx_msg['index']
        if sel == 'LIVE': tf_data = {'tf': '1m', 'limit': 50}
        elif sel == '24H': tf_data = {'tf': '15m', 'limit': 96}
        elif sel == '7D': tf_data = {'tf': '1h', 'limit': 168}
    active = 'LIVE'
    if tf_data['limit'] == 96: active = '24H'
    elif tf_data['limit'] == 168: active = '7D'
    styles = ['control-btn live-btn active' if i['id']['index'] == 'LIVE' and active == 'LIVE' else ('control-btn active' if i['id']['index'] == active else ('control-btn live-btn' if i['id']['index'] == 'LIVE' else 'control-btn')) for i in ctx.inputs_list[0]]
    return tf_data, styles

@app.callback(
    [Output('live-candlestick-chart', 'figure'), Output('live-price-display', 'children'), Output('key-metrics-panel', 'children'), Output('bar-chart-24h', 'figure'), Output('chart-title', 'children'), Output('tradingview-iframe', 'srcDoc')],
    [Input('interval-component', 'n_intervals'), Input('coin-select-dropdown', 'value'), Input('timeframe-store', 'data')]
)
def update_overview(n, selected_symbol, tf_data):
    tv_html = get_tradingview_html(selected_symbol)
    df = generate_chart_data(selected_symbol, tf_data['limit'])
    
    latest_price = df['close'].iloc[-1]
    pct_change = (df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100
    color = '#00CC96' if pct_change >= 0 else '#FF4136'
    
    supply = COIN_PARAMS.get(selected_symbol, {'supply': 0, 'max': 0, 'symbol': 'Crypto'})
    market_cap = latest_price * supply['supply']
    
    metrics = [html.Div(className='market-cap-card', children=[html.Div("Market Cap ⓘ", className='metric-title'), html.Div(format_compact(market_cap), className='metric-value-large')])]
    
    fig = go.Figure(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00CC96', decreasing_line_color='#FF4136'))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=0, r=40, t=10, b=20))
    
    bar_fig = go.Figure(go.Bar(x=['BTC','ETH','SOL'], y=[2.5, -1.2, 5.4], marker_color=['#00CC96', '#FF4136', '#00CC96']))
    bar_fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20))
    
    return fig, html.Span(f"{format_currency(latest_price)}", style={'color': color}), metrics, bar_fig, f"{selected_symbol} Chart", tv_html

@app.callback([Output('markets-table-content', 'children'), Output('trending-content', 'children'), Output('news-content', 'children')], [Input('market-interval', 'n_intervals')])
def update_extras(n):
    market_data = generate_market_snapshot()
    
    # Table
    header = html.Tr([html.Th("Rank"), html.Th("Asset"), html.Th("Price"), html.Th("24h %")])
    rows = [html.Tr([html.Td(c['rank']), html.Td(c['name']), html.Td(format_currency(c['price'])), html.Td(f"{c['change_24h']:.2f}%", className='positive' if c['change_24h']>=0 else 'negative')]) for c in market_data[:10]]
    table = html.Table([html.Thead(header), html.Tbody(rows)], className='crypto-table')
    
    # News
    news = [html.Div(className='news-card', children=[html.Img(src=n['image'], className='news-img'), html.Div(className='news-content', children=[html.Div(n['title'], className='news-title')])]) for n in generate_crypto_news()]
    
    return table, "Trending Data Loading...", news

# --- RUN ---
server = app.server 
if __name__ == '__main__':
    # Force 127.0.0.1 to avoid Windows errors
    print(f"\n✅ Dashboard Live: http://127.0.0.1:8088\n")
    app.run(debug=False, host='127.0.0.1', port=8088)
