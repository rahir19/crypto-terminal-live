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
from datetime import datetime, timedelta
from dash import Dash, dcc, html, ctx, no_update
from dash.dependencies import Input, Output, State, ALL

# --- CONFIGURATION ---
EXCHANGE_ID = 'binance'

SYMBOL_MAP = {
    'BTC/USDT': 'Bitcoin', 'ETH/USDT': 'Ethereum', 'BNB/USDT': 'Binance Coin',
    'SOL/USDT': 'Solana', 'XRP/USDT': 'XRP', 'DOGE/USDT': 'Dogecoin',
    'ADA/USDT': 'Cardano', 'TRX/USDT': 'TRON', 'AVAX/USDT': 'Avalanche',
    'SHIB/USDT': 'Shiba Inu'
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
    {'symbol': 'MEMEAI', 'name': 'MemeAI Coin', 'desc': 'AI generated memes with auto-staking protocol.', 'raised': '85%', 'target': '1000 BNB', 'price': '$0.004', 'category': 'AI'},
    {'symbol': 'BLAST', 'name': 'BlastUp', 'desc': 'Launchpad built on Blast L2 network.', 'raised': '40%', 'target': '5M USD', 'price': '$0.05', 'category': 'DeFi'},
    {'symbol': '5SCAPE', 'name': '5th Scape', 'desc': 'VR & AR gaming ecosystem token.', 'raised': '65%', 'target': '2M USD', 'price': '$0.0018', 'category': 'Gaming'},
    {'symbol': 'DOGE20', 'name': 'Dogecoin20', 'desc': 'Sustainable Dogecoin on Ethereum staking.', 'raised': '92%', 'target': '10M USD', 'price': '$0.0002', 'category': 'Meme'}
]

RWA_ASSETS = [
    {'name': 'Gold', 'ticker': 'PAXG', 'price': 2034.50, 'mkt_cap': 500_000_000, 'type': 'Commodity', 'icon': 'https://assets.coincap.io/assets/icons/paxg@2x.png'},
    {'name': 'Nvidia Corp', 'ticker': 'NVDA', 'price': 145.20, 'mkt_cap': 3_100_000_000_000, 'type': 'Stock', 'icon': 'https://upload.wikimedia.org/wikipedia/commons/2/21/Nvidia_logo.svg'},
    {'name': 'Apple Inc.', 'ticker': 'AAPL', 'price': 225.10, 'mkt_cap': 3_400_000_000_000, 'type': 'Stock', 'icon': 'https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg'},
    {'name': 'Alphabet Inc', 'ticker': 'GOOGL', 'price': 178.30, 'mkt_cap': 2_100_000_000_000, 'type': 'Stock', 'icon': 'https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg'},
    {'name': 'Microsoft Corp', 'ticker': 'MSFT', 'price': 415.50, 'mkt_cap': 3_050_000_000_000, 'type': 'Stock', 'icon': 'https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg'},
    {'name': 'Silver', 'ticker': 'SLV', 'price': 28.40, 'mkt_cap': 1_400_000_000_000, 'type': 'Commodity', 'icon': 'https://assets.coingecko.com/coins/images/12492/small/silver.png'}
]

TRACKER_SYMBOLS = list(SYMBOL_MAP.keys())
DROPDOWN_OPTIONS = [{'label': SYMBOL_MAP[s], 'value': s} for s in TRACKER_SYMBOLS]
DEFAULT_SYMBOL = 'BTC/USDT'
USD_TO_INR_RATE = 89.98

exchange = None
try:
    exchange = getattr(ccxt, EXCHANGE_ID)({'options': {'verify': False}})
    exchange.load_markets()
except Exception as e:
    exchange = None

try: locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
except: pass

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
    return f"https://www.cryptocompare.com/media/37746251/{base}.png"

def get_tradingview_html(symbol):
    tv_symbol = f"BINANCE:{symbol.replace('/', '')}"
    return f"""<!DOCTYPE html><html><head><style>body, html {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #0b0e11; }}</style></head><body><div class="tradingview-widget-container" style="height:100%;width:100%"><div id="tradingview_widget"></div><script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script><script type="text/javascript">new TradingView.widget({{"autosize": true, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Asia/Kolkata", "theme": "dark", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_widget", "details": true, "hotlist": true, "calendar": true, "hide_side_toolbar": false, "backgroundColor": "rgba(11, 14, 17, 1)"}});</script></div></body></html>"""

def generate_crypto_news():
    headlines = ["Bitcoin Surges Past Key Resistance", "Ethereum 2.0 Upgrade Details", "Solana Network Record Transactions", "Crypto Regulation New Bill", "Binance New Partnership", "XRP Ledger Activity Spikes", "Top 5 Altcoins to Watch", "Global Crypto Adoption Growth"]
    sources = ["CoinDesk", "CoinTelegraph", "Decrypt", "Bloomberg", "CryptoSlate"]
    images = ["https://images.unsplash.com/photo-1518546305927-5a555bb7020d?auto=format&fit=crop&w=500&q=60", "https://images.unsplash.com/photo-1621761191319-c6fb62004040?auto=format&fit=crop&w=500&q=60", "https://images.unsplash.com/photo-1622630998477-20aa696fab05?auto=format&fit=crop&w=500&q=60"]
    news_items = []
    random.shuffle(headlines)
    for i in range(6):
        item = {'title': headlines[i], 'source': random.choice(sources), 'time': f"{random.randint(1, 59)} mins ago", 'image': random.choice(images), 'desc': "The cryptocurrency market is witnessing significant movement..."}
        news_items.append(item)
    return news_items

def fetch_chart_data(selected_symbol, timeframe, limit):
    if exchange is None:
        base_price = 5000000 if 'BTC' in selected_symbol else (250000 if 'ETH' in selected_symbol else 10000)
        dates = [datetime.now() - timedelta(minutes=i) for i in range(limit)]
        dates.reverse()
        data = []
        price = base_price
        for d in dates:
            change = random.uniform(-0.005, 0.005)
            open_p = price
            close_p = price * (1 + change)
            high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.002))
            low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.002))
            vol = random.randint(100, 1000)
            data.append([d, open_p, high_p, low_p, close_p, vol])
            price = close_p
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        return df
    try:
        ohlcv = exchange.fetch_ohlcv(selected_symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        for col in ['open', 'high', 'low', 'close']: df[col] = df[col] * USD_TO_INR_RATE
        return df
    except: 
        return None

def fetch_market_data():
    data = []
    if exchange is None:
        for i, (sym, name) in enumerate(SYMBOL_MAP.items()):
            base_price = 5000000 if 'BTC' in sym else (250000 if 'ETH' in sym else random.randint(10, 5000))
            price = base_price * (1 + random.uniform(-0.05, 0.05))
            change_24h = random.uniform(-5, 5)
            volume = random.randint(1000000, 1000000000)
            supply = COIN_PARAMS.get(sym, {}).get('supply', 0)
            mkt_cap = price * supply if supply > 0 else volume * 10
            history = []
            val = price
            for _ in range(15):
                val = val * (1 + random.uniform(-0.02, 0.02))
                history.append(val)
            history.append(price)
            data.append({'rank': i + 1, 'symbol': sym, 'name': name, 'price': price, 'mkt_cap': mkt_cap, 'volume': volume, 'change_24h': change_24h, 'change_7d': change_24h * 1.2, 'history': history})
        return data
    try:
        tickers = exchange.fetch_tickers()
        all_pairs = [s for s in tickers.keys() if s.endswith('/USDT')]
        top_pairs = sorted(all_pairs, key=lambda x: tickers[x]['quoteVolume'], reverse=True)[:100]
        for i, symbol in enumerate(top_pairs):
            t = tickers[symbol]
            base_coin = symbol.split('/')[0]
            price = t['last'] * USD_TO_INR_RATE
            volume = t['quoteVolume'] * USD_TO_INR_RATE
            change_24h = t['percentage']
            supply = COIN_PARAMS.get(symbol, {}).get('supply', 0)
            mkt_cap = price * supply if supply > 0 else volume * 10
            history = []
            val = price
            trend = 1 if change_24h >= 0 else -1
            for _ in range(15):
                val = val * (1 + random.uniform(-0.02, 0.02) * trend)
                history.append(val)
            history.append(price)
            data.append({'rank': i + 1, 'symbol': symbol, 'name': base_coin, 'price': price, 'mkt_cap': mkt_cap, 'volume': volume, 'change_24h': change_24h, 'change_7d': change_24h * 3.2, 'history': history})
    except: pass
    return data

def calculate_cycle_indicators(df):
    if df is None or len(df) < 20: return None, 0, 0, 0 
    df['111DMA'] = df['close'].rolling(window=min(111, len(df)//2)).mean()
    df['350DMA'] = df['close'].rolling(window=min(350, len(df))).mean() * 2
    df['log_price'] = np.log(df['close'])
    df['Rainbow_Base'] = df['close'].rolling(window=min(100, len(df)//2)).mean() 
    df['365DMA'] = df['close'].rolling(window=min(365, len(df))).mean()
    df['Puell'] = df['close'] / df['365DMA'].replace(0, np.nan)
    current_puell = df['Puell'].iloc[-1] if not pd.isna(df['Puell'].iloc[-1]) else 1.0
    puell_meter_val = min(max((current_puell - 0.5) / (3.0 - 0.5) * 100, 0), 100)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    current_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
    pi_denom = df['350DMA'].iloc[-1] if not pd.isna(df['350DMA'].iloc[-1]) else df['close'].iloc[-1]
    price_to_pi = df['close'].iloc[-1] / pi_denom
    top_score = (price_to_pi * 0.6 + (current_rsi/100) * 0.4) * 100
    top_score = min(top_score, 100)
    return df, current_puell, puell_meter_val, top_score

def generate_global_market_data():
    btc_df = fetch_chart_data('BTC/USDT', '1d', 365)
    if btc_df is None: return None
    btc_supply = 19_600_000
    btc_df = btc_df.bfill().ffill()
    total_mkt_cap = btc_df['close'] * btc_supply * 2.0
    total_volume = btc_df['volume'] * 10000 * 5
    return btc_df['timestamp'], total_mkt_cap, total_volume

# --- APP INITIALIZATION ---
app = Dash(__name__, title="Crypto Master", suppress_callback_exceptions=True)
server = app.server  # REQUIRED FOR CLOUD DEPLOYMENT

# --- CSS ---
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Crypto Master</title>
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            :root {
                --bg-color: #0b0e11;
                --card-bg: #151a1e;
                --card-border: #2a2e39;
                --text-main: #eaecef;
                --text-muted: #848e9c;
                --accent-green: #00CC96;
                --accent-red: #FF4136;
                --accent-blue: #2962ff;
                --accent-gold: #FFD700;
                --glass-bg: rgba(21, 26, 30, 0.7);
                --glass-border: rgba(255, 255, 255, 0.08);
            }
            body { 
                background-color: var(--bg-color);
                background-image: radial-gradient(circle at 50% 0%, #1a2233 0%, #0b0e11 60%);
                color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding: 0; overflow-x: hidden;
            }
            .login-container { height: 100vh; width: 100%; background-color: #051025; background-image: linear-gradient(rgba(41, 98, 255, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(41, 98, 255, 0.1) 1px, transparent 1px); background-size: 50px 50px; position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: center; align-items: center; }
            .login-container::before { content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(circle, transparent 40%, #000411 90%); pointer-events: none; }
            .login-nav { position: absolute; top: 0; left: 0; width: 100%; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; z-index: 10; }
            .nav-brand { font-size: 1.5rem; font-weight: 800; color: #fff; text-transform: uppercase; letter-spacing: 1px; }
            .nav-links button { background: none; border: none; color: #ddd; font-size: 0.9rem; font-weight: 600; margin-left: 30px; cursor: pointer; text-transform: uppercase; transition: 0.3s; }
            .nav-links button:hover { color: #00E5FF; }
            .login-box { z-index: 5; max-width: 600px; text-align: left; padding: 40px; }
            .login-title { font-size: 3.5rem; font-weight: 800; color: #fff; margin-bottom: 20px; line-height: 1.1; }
            .login-desc { color: #a0aab8; font-size: 1.1rem; margin-bottom: 40px; line-height: 1.6; }
            .login-input { width: 100%; padding: 15px; margin-bottom: 15px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; font-family: 'Inter', sans-serif; outline: none; transition: 0.3s; font-size: 1rem; display: block; }
            .login-input:focus { border-color: #00E5FF; box-shadow: 0 0 10px rgba(0, 229, 255, 0.2); }
            .login-btn-main { background: linear-gradient(90deg, #00E5FF, #0091EA); color: white; border: none; padding: 15px 40px; font-size: 1rem; font-weight: 700; border-radius: 30px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; text-transform: uppercase; letter-spacing: 1px; display: inline-block; margin-top: 10px; }
            .login-btn-main:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0, 229, 255, 0.4); }
            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 1000; opacity: 0; visibility: hidden; transition: 0.3s; }
            .modal-content { background: #1a2233; padding: 30px; border-radius: 15px; width: 400px; text-align: center; border: 1px solid #333; transform: translateY(20px); transition: 0.3s; }
            .modal-active { opacity: 1; visibility: visible; }
            .modal-active .modal-content { transform: translateY(0); }
            .contact-item { display: flex; align-items: center; margin: 20px 0; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 8px; color: white; text-decoration: none; transition: 0.2s; }
            .contact-item:hover { background: rgba(255,255,255,0.08); }
            .contact-icon { font-size: 1.5rem; margin-right: 15px; width: 30px; text-align: center; color: var(--accent-gold); }
            .close-modal { position: absolute; top: 10px; right: 15px; background: none; border: none; color: #666; font-size: 1.5rem; cursor: pointer; }
            ::-webkit-scrollbar { width: 8px; height: 8px; }
            ::-webkit-scrollbar-track { background: var(--bg-color); }
            ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: #444; }
            .header-title { text-align: center; background: linear-gradient(90deg, #FFD700 0%, #FDB931 50%, #FFD700 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding: 25px 0; font-size: 2.5rem; font-weight: 800; letter-spacing: 1px; text-shadow: 0px 4px 20px rgba(255, 215, 0, 0.3); }
            .custom-tabs-container { margin: 0 20px 20px 20px; border: none !important; }
            .custom-tabs { border-bottom: 1px solid var(--card-border); background: transparent !important; }
            .custom-tab { background-color: transparent !important; color: var(--text-muted) !important; border: none !important; padding: 15px 25px; font-size: 1rem; font-weight: 500; transition: all 0.3s ease; cursor: pointer; }
            .custom-tab:hover { color: #fff !important; }
            .custom-tab--selected { color: var(--accent-gold) !important; border-bottom: 2px solid var(--accent-gold) !important; font-weight: 600; background: linear-gradient(180deg, rgba(255, 215, 0, 0) 0%, rgba(255, 215, 0, 0.05) 100%) !important; }
            .chart-wrapper, .metrics-container, .bottom-bar-chart, .analytics-card, .trending-card, .news-card, .spot-card, .rwa-card, .presale-card, .dex-card { background: var(--glass-bg); backdrop-filter: blur(10px); border: 1px solid var(--glass-border); border-radius: 12px; box-shadow: 0 4px 24px -1px rgba(0,0,0,0.2); transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; }
            .news-card:hover, .presale-card:hover, .dex-card:hover { transform: translateY(-4px); box-shadow: 0 10px 30px -5px rgba(0,0,0,0.4); border-color: var(--accent-gold); }
            .control-panel { margin: 0 auto 20px auto; text-align: center; width: 100%; max-width: 400px; }
            .control-bar-container { display: flex; justify-content: space-between; align-items: center; background-color: rgba(255,255,255,0.02); padding: 12px 20px; border-radius: 12px 12px 0 0; border-bottom: 1px solid var(--glass-border); }
            .btn-group { display: flex; background-color: #0b0e11; border-radius: 8px; padding: 4px; gap: 4px; border: 1px solid #222; }
            .control-btn { background: transparent; border: none; color: var(--text-muted); padding: 6px 14px; font-size: 0.85rem; cursor: pointer; border-radius: 6px; font-weight: 600; transition: 0.2s; }
            .control-btn:hover { color: #fff; background-color: rgba(255,255,255,0.05); }
            .control-btn.active { background-color: #2a2e39; color: #fff; }
            .control-btn.live-btn { color: var(--accent-red); }
            .control-btn.live-btn.active { background-color: rgba(255, 65, 54, 0.15); color: var(--accent-red); box-shadow: 0 0 10px rgba(255, 65, 54, 0.2); }
            .live-price-big { text-align: center; font-size: 3.5rem; font-weight: 700; color: #fff; margin: 20px 0; letter-spacing: -1px; }
            .metric-box { background-color: rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; text-align: center; border: 1px solid transparent; }
            .metric-box:hover { border-color: #333; background-color: rgba(255,255,255,0.05); }
            .metric-title { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
            .metric-value { font-size: 1.1rem; color: #fff; font-weight: 600; }
            .crypto-table { width: 100%; border-collapse: separate; border-spacing: 0; color: #fff; font-size: 0.95rem; }
            .crypto-table th { text-align: left; padding: 16px; color: var(--text-muted); font-size: 0.8rem; font-weight: 600; border-bottom: 1px solid var(--card-border); }
            .crypto-table td { padding: 16px; border-bottom: 1px solid #222; vertical-align: middle; transition: background 0.2s; }
            .crypto-table tr:hover td { background-color: rgba(255,255,255,0.03); }
            .coin-cell { display: flex; align-items: center; gap: 12px; }
            .coin-icon { width: 32px; height: 32px; border-radius: 50%; box-shadow: 0 2px 5px rgba(0,0,0,0.3); }
            .positive { color: var(--accent-green); font-weight: 600; text-shadow: 0 0 10px rgba(0, 204, 150, 0.2); }
            .negative { color: var(--accent-red); font-weight: 600; text-shadow: 0 0 10px rgba(255, 65, 54, 0.2); }
            .flex-container { display: flex; gap: 24px; padding: 0 24px; }
            .chart-wrapper { flex: 3; min-width: 600px; padding-bottom: 10px; }
            .metrics-container { flex: 1; height: fit-content; padding: 24px; }
            .market-cap-card { background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(255,255,255,0.01) 100%); border: 1px solid var(--accent-gold); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; }
            .Select-control { background-color: #1a1e23 !important; border: 1px solid #333 !important; color: white !important; }
            .Select-menu-outer { background-color: #1a1e23 !important; border: 1px solid #333 !important; }
            .Select-value-label { color: white !important; }
            .page-btn { background: var(--accent-gold); color: #000; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 700; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 10px rgba(255, 215, 0, 0.3); }
            .page-btn:hover:not(:disabled) { background: #e6c200; transform: translateY(-2px); }
            .page-btn:disabled { background: #333; color: #666; box-shadow: none; cursor: default; }
            .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
            .analytics-grid, .spot-grid, .rwa-grid { display: grid; gap: 24px; padding: 24px; }
            .analytics-grid { grid-template-columns: 2fr 1fr; }
            .spot-grid { grid-template-columns: 2fr 1fr; }
            .rwa-grid { grid-template-columns: 2fr 1fr 1fr; }
            .news-grid, .presale-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; padding: 24px; }
            .meter-bar-container { background-color: #222; height: 10px; border-radius: 5px; margin: 20px 0; position: relative; overflow: visible; }
            .meter-bar-puell { background: linear-gradient(90deg, #00CC96 20%, #444 50%, #FF4136 80%); height: 100%; border-radius: 5px; opacity: 0.8; }
            .meter-bar-top { background: linear-gradient(90deg, #00CC96, #FF4136); height: 100%; border-radius: 5px; opacity: 0.8; }
            .meter-knob { width: 16px; height: 16px; background: var(--accent-gold); border-radius: 50%; position: absolute; top: -3px; border: 2px solid #0b0e11; box-shadow: 0 0 10px rgba(255, 215, 0, 0.8); transition: left 0.5s cubic-bezier(0.4, 0.0, 0.2, 1); }
            .dex-scroll-container { display: flex; gap: 20px; overflow-x: auto; padding: 10px 20px 20px 20px; }
            .dex-card { min-width: 340px; background: #151a1e; padding: 20px; }
            .dex-row { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
            .trending-wrapper { display: flex; gap: 24px; padding: 24px; flex-wrap: wrap; }
            .trending-card { flex: 1; min-width: 350px; padding: 24px; }
            .news-img { width: 100%; height: 180px; object-fit: cover; opacity: 0.9; transition: opacity 0.3s; }
            .news-card:hover .news-img { opacity: 1; }
            .news-content { padding: 20px; }
            .presale-btn { width: 100%; background: linear-gradient(90deg, #FFD700, #FFA500); border: none; color: #000; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer; transition: 0.3s; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
            .presale-btn:hover { opacity: 0.9; box-shadow: 0 0 15px rgba(255, 215, 0, 0.5); }
            footer { padding: 20px; text-align: center; color: #444; font-size: 0.8rem; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# --- LAYOUTS ---
login_layout = html.Div(className='login-container', children=[
    html.Div(className='login-nav', children=[
        html.Div("CRYPTO MASTER", className='nav-brand'),
        html.Div(className='nav-links', children=[html.Button("ABOUT", id='about-btn'), html.Button("CONTACT", id='contact-btn')])
    ]),
    html.Div(className='login-box', children=[
        html.H1("Welcome To Our Company", className='login-title'),
        html.P("Explore the world of cryptocurrency market analysis, real-time data, and advanced trading indicators in one professional terminal. Secure. Fast. Reliable.", className='login-desc'),
        dcc.Input(id='username-box', type='text', placeholder='Username (admin)', className='login-input'),
        dcc.Input(id='password-box', type='password', placeholder='Password (admin)', className='login-input'),
        html.Div(id='login-error', style={'color': '#FF4136', 'marginBottom': '10px', 'fontSize': '0.9rem'}),
        html.Button("LOGIN", id='login-button', className='login-btn-main')
    ]),
    html.Div(id='about-modal', className='modal-overlay', children=[
        html.Div(className='modal-content', children=[
            html.Button("×", id='close-about', className='close-modal'),
            html.H2("About Crypto Master", style={'color': '#fff', 'marginBottom': '15px'}),
            html.P("Crypto Master is a state-of-the-art dashboard built with Python and Dash. It simulates real-time crypto exchanges, provides technical analysis tools like Puell Multiple and Pi Cycle Top, and tracks upcoming presales.", style={'color': '#ccc', 'lineHeight': '1.6'}),
        ])
    ]),
    html.Div(id='contact-modal', className='modal-overlay', children=[
        html.Div(className='modal-content', children=[
            html.Button("×", id='close-contact', className='close-modal'),
            html.H2("Contact Me", style={'color': '#fff', 'marginBottom': '25px'}),
            html.Div(className='contact-item', children=[html.I(className="fas fa-user contact-icon"), html.Span("Raghav Ahir Yaduvanshi", style={'fontSize': '1.1rem', 'fontWeight': 'bold'})]),
            html.Div(className='contact-item', children=[html.I(className="fas fa-phone contact-icon"), html.Span("6266649445")]),
            html.A(href="https://www.linkedin.com/in/raghav-ahir-117b8b357/", target="_blank", className='contact-item', children=[html.I(className="fab fa-linkedin contact-icon"), html.Span("LinkedIn Profile")]),
            html.A(href="https://github.com/rahir19", target="_blank", className='contact-item', children=[html.I(className="fab fa-github contact-icon"), html.Span("GitHub Profile")]),
        ])
    ])
])

dashboard_layout = html.Div([
    dcc.Store(id='timeframe-store', data={'tf': '1m', 'limit': 50}), 
    dcc.Store(id='current-page-store', data=1),
    html.Div("⚡CRYPTO MASTER", className='header-title'),
    dcc.Tabs(parent_className='custom-tabs', className='custom-tabs-container', children=[
        dcc.Tab(label='Overview', className='custom-tab', selected_className='custom-tab--selected', children=[
            html.Div(className='control-panel', children=[html.P("SELECT ASSET", style={'marginBottom': '8px', 'color': '#888', 'fontSize': '0.75rem', 'letterSpacing': '1px'}), dcc.Dropdown(id='coin-select-dropdown', options=DROPDOWN_OPTIONS, value=DEFAULT_SYMBOL, clearable=False, style={'color': '#000'})]),
            html.H2(id='live-price-display', className='live-price-big'),
            html.Div(className='flex-container', children=[
                html.Div(className='chart-wrapper', children=[
                    html.Div(className='control-bar-container', children=[html.Div(className='btn-group', children=[html.Button("Price", className='control-btn active'), html.Button("Market Cap", className='control-btn'), html.Button("TradingView", className='control-btn')]), html.Div(className='btn-group', children=[html.Button("LIVE", id={'type': 'tf-btn', 'index': 'LIVE'}, className='control-btn live-btn active'), html.Button("24H", id={'type': 'tf-btn', 'index': '24H'}, className='control-btn'), html.Button("7D", id={'type': 'tf-btn', 'index': '7D'}, className='control-btn'), html.Button("1M", id={'type': 'tf-btn', 'index': '1M'}, className='control-btn'), html.Button("1Y", id={'type': 'tf-btn', 'index': '1Y'}, className='control-btn'), html.Button("5Y", id={'type': 'tf-btn', 'index': '5Y'}, className='control-btn')])]),
                    html.Div(style={'padding': '20px'}, children=[html.H3(id='chart-title', style={'borderBottom': '1px solid #333', 'paddingBottom': '15px', 'marginTop': '0', 'fontSize': '1.1rem', 'color': '#fff'}), dcc.Graph(id='live-candlestick-chart', style={'height': '480px'})])
                ]),
                html.Div(className='metrics-container', children=[html.Div(id='key-metrics-panel')]),
            ]),
            html.Div(className='bottom-bar-chart', style={'margin': '24px'}, children=[html.H4("MARKET PERFORMANCE (24H)", style={'color': '#888', 'marginBottom': '15px', 'letterSpacing': '1px'}), dcc.Graph(id='bar-chart-24h', style={'height': '300px'})])
        ]),
        dcc.Tab(label='Technical Analysis', className='custom-tab', selected_className='custom-tab--selected', children=[
            html.Div(className='control-panel', style={'marginTop': '20px'}, children=[html.P("SELECT ASSET FOR ANALYSIS", style={'marginBottom': '8px', 'color': '#888', 'fontSize': '0.75rem'}), dcc.Dropdown(id='analysis-coin-dropdown', options=DROPDOWN_OPTIONS, value=DEFAULT_SYMBOL, clearable=False, style={'color': '#000'})]),
            html.Div(className='analytics-grid', children=[
                html.Div([
                    html.Div(className='analytics-card', style={'marginBottom': '20px', 'padding': '20px'}, children=[html.Div([html.Span("Pi Cycle Top Indicator"), html.Span("111DMA vs 350DMA x2", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title', style={'display':'flex','justifyContent':'space-between','marginBottom':'15px','fontWeight':'bold'}), dcc.Graph(id='pi-cycle-chart', style={'height': '320px'})]),
                    html.Div(className='analytics-card', style={'marginBottom': '20px', 'padding': '20px'}, children=[html.Div([html.Span("Rainbow Price Chart"), html.Span("Long Term Trend", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title', style={'display':'flex','justifyContent':'space-between','marginBottom':'15px','fontWeight':'bold'}), dcc.Graph(id='rainbow-chart', style={'height': '320px'})]),
                    html.Div(className='analytics-card', style={'padding': '20px'}, children=[html.Div([html.Span("Puell Multiple Chart"), html.Span("Buy/Sell Zones", style={'color': '#888', 'fontSize': '0.8rem'})], className='card-title', style={'display':'flex','justifyContent':'space-between','marginBottom':'15px','fontWeight':'bold'}), dcc.Graph(id='puell-chart', style={'height': '320px'})])
                ]),
                html.Div([
                    html.Div(className='analytics-card', style={'marginBottom': '20px', 'padding': '25px', 'textAlign': 'center'}, children=[html.Div("PUELL MULTIPLE STATUS", style={'color':'#888','fontSize':'0.8rem'}), html.Div(id='puell-val-text', className='big-stat', style={'fontSize':'2.5rem','fontWeight':'bold','margin':'10px 0'}), html.Div(className='meter-bar-container', children=[html.Div(className='meter-bar-puell'), html.Div(id='puell-knob', className='meter-knob')]), html.Div(className='meter-labels', style={'display':'flex','justifyContent':'space-between','color':'#888','fontSize':'0.8rem'}, children=[html.Span("Undervalued"), html.Span("Overvalued")])]),
                    html.Div(className='analytics-card', style={'marginBottom': '20px', 'padding': '25px', 'textAlign': 'center'}, children=[html.Div("CYCLE TOP INDICATOR", style={'color':'#888','fontSize':'0.8rem'}), html.Div(id='top-val-text', className='big-stat', style={'fontSize':'2.5rem','fontWeight':'bold','margin':'10px 0'}), html.Div(className='meter-bar-container', children=[html.Div(className='meter-bar-top'), html.Div(id='top-knob', className='meter-knob')]), html.Div(className='meter-labels', style={'display':'flex','justifyContent':'space-between','color':'#888','fontSize':'0.8rem'}, children=[html.Span("Hold"), html.Span("Sell")])]),
                    html.Div(className='analytics-card', style={'textAlign': 'center', 'padding': '25px'}, children=[html.Div("MARKET REGIME", style={'color':'#888','fontSize':'0.8rem'}), html.H2(id='cycle-status-text', style={'color': '#fff', 'margin': '15px 0', 'fontSize': '1.8rem'}), html.Div(id='cycle-desc', style={'color': '#888', 'fontSize': '0.9rem', 'lineHeight': '1.5'})]),
                ])
            ])
        ]),
        dcc.Tab(label='RWA Assets', className='custom-tab', selected_className='custom-tab--selected', children=[
            html.Div(className='rwa-grid', children=[
                html.Div(className='rwa-card', children=[html.Div([html.H3("Total Tokenized Market Cap", style={'color':'#aaa', 'fontSize':'0.9rem'}), html.Div([html.Span("$16.24B", style={'fontSize':'2.2rem', 'fontWeight':'bold'}), html.Span(" +1.12%", style={'color':'#FF4136', 'fontSize':'1rem', 'marginLeft':'10px'})])], style={'paddingBottom':'15px', 'borderBottom':'1px solid #333', 'marginBottom':'15px'}), dcc.Graph(id='rwa-mkt-chart', style={'height': '220px'})]),
                html.Div(className='rwa-card', children=[html.H4("TOP ISSUERS", style={'color':'#fff', 'textAlign':'center', 'marginBottom':'20px'}), dcc.Graph(id='rwa-issuer-chart', style={'height': '250px'})]),
                html.Div(className='rwa-card', children=[html.H4("TOP NETWORKS", style={'color':'#fff', 'textAlign':'center', 'marginBottom':'20px'}), dcc.Graph(id='rwa-network-chart', style={'height': '250px'})])
            ]),
            html.Div(className='rwa-table-container', style={'padding':'0 24px 24px 24px'}, children=[html.H3("RWA TOKEN LIST", style={'color':'white', 'marginBottom':'20px', 'fontSize':'1.2rem'}), html.Div(id='rwa-table-content')])
        ]),
        dcc.Tab(label='Global Market', className='custom-tab', selected_className='custom-tab--selected', children=[
            html.Div(className='spot-grid', children=[
                html.Div([html.Div(className='analytics-card', style={'marginBottom': '24px', 'padding': '24px'}, children=[html.Div([html.Div([html.H3("TOTAL CRYPTO MARKET CAP", style={'color':'#888', 'marginBottom':'10px', 'fontSize':'0.8rem'}), html.Div([html.Span(id='global-mkt-cap', className='mkt-cap-main', style={'fontSize':'3rem','fontWeight':'bold'}), html.Span(id='global-mkt-change', className='mkt-cap-change')])])], style={'display':'flex', 'justifyContent':'space-between'}), dcc.Graph(id='global-mkt-chart', style={'height': '320px'})]), html.Div(className='analytics-card', style={'padding': '24px'}, children=[html.H4("SPOT VOLUME (24H)", style={'color':'#fff', 'marginBottom':'20px'}), dcc.Graph(id='global-vol-chart', style={'height': '300px'})])]),
                html.Div([html.Div(className='analytics-card', style={'marginBottom': '24px', 'padding': '24px'}, children=[html.H4("HISTORICAL SNAPSHOTS", style={'color':'#fff', 'marginBottom':'20px'}), html.Div(className='stat-grid', children=[html.Div(className='stat-card', children=[html.Div("Yesterday", className='stat-label'), html.Div(id='hist-1d', className='stat-val')]), html.Div(className='stat-card', children=[html.Div("Last Week", className='stat-label'), html.Div(id='hist-7d', className='stat-val')]), html.Div(className='stat-card', children=[html.Div("Last Month", className='stat-label'), html.Div(id='hist-30d', className='stat-val')]), html.Div(className='stat-card', children=[html.Div("Last Year", className='stat-label'), html.Div(id='hist-1y', className='stat-val')])]), html.H4("YEARLY RANGE", style={'color':'#fff', 'marginTop':'30px', 'marginBottom':'15px'}), html.Div(className='stat-grid', children=[html.Div(className='stat-card', children=[html.Div("Yearly High", className='stat-label'), html.Div(id='year-high', className='stat-val', style={'color':'#00CC96'})]), html.Div(className='stat-card', children=[html.Div("Yearly Low", className='stat-label'), html.Div(id='year-low', className='stat-val', style={'color':'#FF4136'})])])]), html.Div(className='analytics-card', style={'padding': '24px'}, children=[html.H4("EXCHANGE DOMINANCE", style={'color':'#fff', 'marginBottom':'20px'}), dcc.Graph(id='cex-dominance-chart', style={'height': '300px'})])])
            ])
        ]),
        dcc.Tab(label='TradingView', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'height': '800px', 'padding': '24px'}, children=[html.Div(style={'width': '100%', 'height': '100%', 'borderRadius': '12px', 'overflow': 'hidden', 'boxShadow': '0 10px 30px rgba(0,0,0,0.5)'}, children=[html.Iframe(id='tradingview-iframe', style={'width': '100%', 'height': '100%', 'border': 'none'})])])]),
        dcc.Tab(label='Screeners', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(className='market-table-container', style={'padding': '24px'}, children=[html.H2("TOP 100 CRYPTOCURRENCIES", style={'color': 'white', 'marginBottom': '25px', 'fontSize': '1.5rem'}), html.Div(id='markets-table-content', style={'overflowX': 'auto', 'borderRadius': '12px', 'border': '1px solid #2a2e39'}, children="Loading Market Data..."), html.Div(className='pagination-container', children=[html.Button("< Prev", id='prev-btn', className='page-btn'), html.Span(id='page-display', className='page-text', children="Page 1 of 10"), html.Button("Next >", id='next-btn', className='page-btn')])])]),
        dcc.Tab(label='DexScan', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(style={'padding': '24px'}, children=[html.H2("LIVE DEX PAIRS (SIMULATED)", style={'color': 'white', 'marginBottom': '25px'}), html.Div(id='dexscan-content', className='dex-scroll-container', children="Loading DexScan...")])]),
        dcc.Tab(label='Upcoming Sales', className='custom-tab', selected_className='custom-tab--selected', children=[
            html.Div(style={'padding': '24px'}, children=[
                html.H2("🚀 HIGH POTENTIAL PRESALES", style={'color': '#00CC96', 'marginBottom': '30px', 'textAlign': 'center', 'letterSpacing': '2px'}),
                html.Div(className='presale-grid', children=[html.Div(className='presale-card', children=[html.Div(p['category'], className='presale-badge'), html.Div(className='presale-header', children=[html.Div(p['symbol'][:2], className='presale-icon'), html.Div([html.Div(p['name'], className='presale-title'), html.Div(p['symbol'], className='presale-symbol')])]), html.P(p['desc'], className='presale-desc'), html.Div(className='progress-container', children=[html.Div(className='progress-labels', children=[html.Span(f"Raised: {p['raised']}"), html.Span(f"Target: {p['target']}")]) , html.Div(className='progress-bar-bg', children=[html.Div(className='progress-bar-fill', style={'width': p['raised']})])]), html.Div(f"Entry Price: {p['price']}", className='countdown'), html.Button("VIEW DETAILS", className='presale-btn')]) for p in UPCOMING_PROJECTS])
            ])
        ]),
        dcc.Tab(label='Trending', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='trending-content', className='trending-wrapper', children="Loading Trending Data...")]),
        dcc.Tab(label='News Feed', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='news-content', className='news-grid', children="Loading Latest Crypto News...")])
    ]),
    dcc.Interval(id='interval-component', interval=2000, n_intervals=0),
    dcc.Interval(id='market-interval', interval=10000, n_intervals=0)
])

# --- FIX: INITIAL LAYOUT MUST CONTAIN LOGIN PAGE CONTENT TO RENDER ---
app.layout = html.Div([
    dcc.Store(id='login-state', data=False),
    # HERE IS THE FIX: Initialize 'children' with login_layout
    html.Div(id='page-content', children=login_layout)
])

# --- CALLBACKS ---
@app.callback(
    [Output('page-content', 'children'), Output('login-error', 'children')],
    [Input('login-button', 'n_clicks')],
    [State('username-box', 'value'), State('password-box', 'value'), State('login-state', 'data')],
    prevent_initial_call=False
)
def manage_login(n_clicks, username, password, is_logged_in):
    if n_clicks is None: return no_update, no_update
    if username == "admin" and password == "admin": return dashboard_layout, ""
    return login_layout, "Invalid Credentials (Try: admin/admin)"

@app.callback(Output('contact-modal', 'className'), [Input('contact-btn', 'n_clicks'), Input('close-contact', 'n_clicks')], [State('contact-modal', 'className')])
def toggle_contact_modal(open_click, close_click, current_class):
    if not ctx.triggered: return "modal-overlay"
    return "modal-overlay modal-active" if 'contact-btn' in ctx.triggered_id else "modal-overlay"

@app.callback(Output('about-modal', 'className'), [Input('about-btn', 'n_clicks'), Input('close-about', 'n_clicks')], [State('about-modal', 'className')])
def toggle_about_modal(open_click, close_click, current_class):
    if not ctx.triggered: return "modal-overlay"
    return "modal-overlay modal-active" if 'about-btn' in ctx.triggered_id else "modal-overlay"

# --- ALL DASHBOARD CALLBACKS (KEPT UNCHANGED) ---
@app.callback([Output('rwa-mkt-chart', 'figure'), Output('rwa-issuer-chart', 'figure'), Output('rwa-network-chart', 'figure'), Output('rwa-table-content', 'children')], Input('interval-component', 'n_intervals'))
def update_rwa(n):
    x_vals = list(range(30)); y_vals = [3.2 + (i*0.01 + random.uniform(-0.05, 0.05)) for i in x_vals]
    fig_mkt = go.Figure(go.Scatter(x=x_vals, y=y_vals, mode='lines', fill='tozeroy', line=dict(color='#00CC96', width=3), fillcolor='rgba(0, 204, 150, 0.1)')); fig_mkt.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False))
    fig_issuer = go.Figure(go.Pie(labels=['Tether', 'Paxos', 'Ondo', 'Backed'], values=[43, 38, 10, 9], hole=0.7, textinfo='none', marker=dict(colors=['#2962ff', '#00CC96', '#F5B97F', '#FF4136']))); fig_issuer.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=0, b=20), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    fig_net = go.Figure(go.Pie(labels=['Ethereum', 'Solana', 'Arbitrum'], values=[93, 6, 1], hole=0.7, textinfo='none', marker=dict(colors=['#2962ff', '#00CC96', '#F5B97F']))); fig_net.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=0, b=20), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    header = html.Tr([html.Th("#"), html.Th("NAME"), html.Th("TYPE"), html.Th("PRICE"), html.Th("CHANGE (24H)"), html.Th("MARKET CAP")]); rows = []
    for i, asset in enumerate(RWA_ASSETS):
        price = asset['price'] * (1 + random.uniform(-0.001, 0.001)); change = random.uniform(-1.5, 2.5); col = 'positive' if change >= 0 else 'negative'
        rows.append(html.Tr([html.Td(i+1, style={'color':'#666'}), html.Td(html.Div(className='coin-cell', children=[html.Img(src=asset['icon'], className='coin-icon'), html.Div([html.Div(asset['name'], style={'fontWeight': '600'}), html.Div(asset['ticker'], className='coin-symbol', style={'fontSize':'0.75rem', 'color':'#888'})])])), html.Td(asset['type'], style={'color':'#aaa', 'fontSize':'0.85rem'}), html.Td(format_currency(price), style={'fontWeight': '600', 'fontFamily':'monospace'}), html.Td(f"{change:+.2f}%", className=col), html.Td(format_compact(asset['mkt_cap']), style={'color':'#ccc'})]))
    return fig_mkt, fig_issuer, fig_net, html.Table([html.Thead(header), html.Tbody(rows)], className='crypto-table')

@app.callback([Output('global-mkt-cap', 'children'), Output('global-mkt-change', 'children'), Output('global-mkt-chart', 'figure'), Output('global-vol-chart', 'figure'), Output('cex-dominance-chart', 'figure'), Output('hist-1d', 'children'), Output('hist-7d', 'children'), Output('hist-30d', 'children'), Output('hist-1y', 'children'), Output('year-high', 'children'), Output('year-low', 'children')], Input('interval-component', 'n_intervals'))
def update_spot_market(n):
    data = generate_global_market_data(); 
    if not data: return "Loading...", "", go.Figure(), go.Figure(), go.Figure(), "-", "-", "-", "-", "-", "-"
    times, mkt_caps, volumes = data; current_cap = mkt_caps.iloc[-1]; prev_cap = mkt_caps.iloc[-2]; change = ((current_cap - prev_cap) / prev_cap) * 100; color = '#00CC96' if change >= 0 else '#FF4136'
    fig_cap = go.Figure(go.Scatter(x=times, y=mkt_caps, mode='lines', fill='tozeroy', line=dict(color='#2962ff', width=3), fillcolor='rgba(41, 98, 255, 0.1)')); fig_cap.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=10, t=10, b=30), height=320, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'))
    fig_vol = go.Figure(go.Bar(x=times, y=volumes, marker_color='#00CC96')); fig_vol.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=10, t=10, b=30), height=300, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'))
    x_vals = times[-90:]; y_binance = np.random.normal(50, 2, 90); y_coinbase = np.random.normal(15, 1, 90); y_dex = np.random.normal(20, 3, 90); y_others = 100 - (y_binance + y_coinbase + y_dex); fig_dom = go.Figure(); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_binance, stackgroup='one', name='Binance', line=dict(width=0))); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_coinbase, stackgroup='one', name='Coinbase', line=dict(width=0))); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_dex, stackgroup='one', name='DEXs', line=dict(width=0))); fig_dom.add_trace(go.Scatter(x=x_vals, y=y_others, stackgroup='one', name='Others', line=dict(width=0))); fig_dom.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=10, t=10, b=30), height=300, legend=dict(orientation="h", y=1.1))
    return format_compact(current_cap), html.Span(f"{change:+.2f}% (24h)", style={'color': color, 'fontSize': '1.2rem'}), fig_cap, fig_vol, fig_dom, format_compact(mkt_caps.iloc[-2]), format_compact(mkt_caps.iloc[-8]), format_compact(mkt_caps.iloc[-31]), format_compact(mkt_caps.iloc[0]), format_compact(mkt_caps.max()), format_compact(mkt_caps.min())

@app.callback([Output('pi-cycle-chart', 'figure'), Output('rainbow-chart', 'figure'), Output('puell-chart', 'figure'), Output('puell-val-text', 'children'), Output('puell-knob', 'style'), Output('top-val-text', 'children'), Output('top-knob', 'style'), Output('cycle-status-text', 'children'), Output('cycle-desc', 'children')], [Input('interval-component', 'n_intervals'), Input('analysis-coin-dropdown', 'value')])
def update_analytics(n, selected_symbol):
    if not selected_symbol: return go.Figure(), go.Figure(), go.Figure(), "", {}, "", {}, "", ""
    df = fetch_chart_data(selected_symbol, '1d', 2000); df, current_puell, puell_meter_val, top_score = calculate_cycle_indicators(df)
    if df is None: return go.Figure(), go.Figure(), go.Figure(), "N/A", {}, "N/A", {}, "No Data", "Select BTC/ETH"
    fig_pi = go.Figure(); fig_pi.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='Price', line=dict(color='rgba(255,255,255,0.8)', width=1))); fig_pi.add_trace(go.Scatter(x=df['timestamp'], y=df['111DMA'], mode='lines', name='111 DMA', line=dict(color='#00CC96', width=2))); fig_pi.add_trace(go.Scatter(x=df['timestamp'], y=df['350DMA'], mode='lines', name='350 DMA x2', line=dict(color='#FF4136', width=2))); fig_pi.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=30, r=10, t=10, b=30), legend=dict(orientation="h", y=1.1), yaxis=dict(gridcolor='rgba(255,255,255,0.05)'), xaxis=dict(showgrid=False))
    fig_rain = go.Figure(); base = df['Rainbow_Base']; colors = ['#6a0dad', '#2962ff', '#00CC96', '#FFD700', '#FF8C00', '#FF4136']; multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75]
    for i, mult in enumerate(multipliers): fig_rain.add_trace(go.Scatter(x=df['timestamp'], y=base*mult, mode='lines', line=dict(width=0), showlegend=False, fill='tonexty' if i>0 else 'none', fillcolor=colors[i], opacity=0.3))
    fig_rain.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='Price', line=dict(color='white', width=2))); fig_rain.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=30, r=10, t=10, b=30), showlegend=False, yaxis_type="log", yaxis=dict(gridcolor='rgba(255,255,255,0.05)'), xaxis=dict(showgrid=False))
    fig_puell = go.Figure(); fig_puell.add_hrect(y0=4, y1=10, fillcolor="rgba(255, 65, 54, 0.2)", line_width=0); fig_puell.add_hrect(y0=0, y1=0.5, fillcolor="rgba(0, 204, 150, 0.2)", line_width=0); fig_puell.add_trace(go.Scatter(x=df['timestamp'], y=df['Puell'], mode='lines', name='Puell Multiple', line=dict(color='#2962ff', width=2))); fig_puell.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=30, r=10, t=10, b=30), yaxis_title="Multiple", yaxis=dict(gridcolor='rgba(255,255,255,0.05)'), xaxis=dict(showgrid=False))
    puell_text = f"{current_puell:.2f}"; puell_style = {'left': f'{puell_meter_val}%'}; top_text = f"{top_score:.1f}%"; top_style = {'left': f'{top_score}%'}; dma_200 = df['close'].rolling(window=200).mean().iloc[-1] if not pd.isna(df['close'].rolling(window=200).mean().iloc[-1]) else 0; val_score = 50; 
    if dma_200 > 0: val_score = min(max((df['close'].iloc[-1] / dma_200 - 0.5) / 1.9 * 100, 0), 100)
    status = "NEUTRAL"; desc = "Market is currently within expected ranges."; 
    if val_score > 80: status = "OVERHEATED (SELL)"; desc = "Prices are extended. Caution advised."
    elif val_score < 20: status = "ACCUMULATION (BUY)"; desc = "Historical buy zone detected."
    return fig_pi, fig_rain, fig_puell, puell_text, puell_style, top_text, top_style, status, desc

@app.callback([Output('timeframe-store', 'data'), Output({'type': 'tf-btn', 'index': ALL}, 'className'), Output('interval-component', 'interval')], [Input({'type': 'tf-btn', 'index': ALL}, 'n_clicks')], [State('timeframe-store', 'data')])
def update_controls(n_clicks, current_tf_data):
    ctx_msg = ctx.triggered_id; tf_data = current_tf_data; interval_speed = 2000 
    if ctx_msg and ctx_msg['type'] == 'tf-btn':
        selected_tf = ctx_msg['index']
        if selected_tf == 'LIVE': tf_data = {'tf': '1m', 'limit': 50}; interval_speed = 2000
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

@app.callback([Output('live-candlestick-chart', 'figure'), Output('live-price-display', 'children'), Output('key-metrics-panel', 'children'), Output('bar-chart-24h', 'figure'), Output('chart-title', 'children'), Output('tradingview-iframe', 'srcDoc')], [Input('interval-component', 'n_intervals'), Input('coin-select-dropdown', 'value'), Input('timeframe-store', 'data')])
def update_overview(n, selected_symbol, tf_data):
    if not selected_symbol: return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    tv_html = get_tradingview_html(selected_symbol); tickers = {}; 
    try: tickers = exchange.fetch_tickers(TRACKER_SYMBOLS) if exchange else {}; selected_ticker = tickers.get(selected_symbol, {})
    except: tickers = {}; selected_ticker = {}
    df = fetch_chart_data(selected_symbol, tf_data['tf'], tf_data['limit'])
    if df is None: return go.Figure(), "Loading...", "Loading...", go.Figure(), "Loading...", tv_html
    latest_price = selected_ticker.get('last', df['close'].iloc[-1]) * USD_TO_INR_RATE; pct_change = selected_ticker.get('percentage', 0); volume = selected_ticker.get('quoteVolume', 0) * USD_TO_INR_RATE; color = '#00CC96' if pct_change >= 0 else '#FF4136'; full_name = SYMBOL_MAP.get(selected_symbol, selected_symbol)
    supply = COIN_PARAMS.get(selected_symbol, {'supply': 0, 'max': 0, 'symbol': 'Crypto'}); market_cap = latest_price * supply['supply']; fdv = latest_price * supply['max'] if supply['max'] else market_cap
    metrics_html = [html.Div(className='market-cap-card', children=[html.Div("MARKET CAP", className='metric-title'), html.Div(format_compact(market_cap), className='metric-value-large', style={'fontSize':'1.8rem'}), html.Div(f"{pct_change:+.2f}%", style={'color': color, 'fontSize': '1rem', 'marginTop': '5px', 'fontWeight': 'bold'})]), html.Div(className='metric-grid', children=[html.Div(className='metric-box', children=[html.Div("Volume (24h)", className='metric-title'), html.Div(format_compact(volume), className='metric-value')]), html.Div(className='metric-box', children=[html.Div("FDV", className='metric-title'), html.Div(format_compact(fdv), className='metric-value')]), html.Div(className='metric-box', children=[html.Div("Vol/Mkt Cap", className='metric-title'), html.Div(f"{(volume/market_cap*100):.2f}%" if market_cap > 0 else "N/A", className='metric-value')]), html.Div(className='metric-box', children=[html.Div("Total Supply", className='metric-title'), html.Div(f"{format_compact(supply['supply']).replace('₹ ', '')}", className='metric-value')]), html.Div(className='metric-box', children=[html.Div("Max Supply", className='metric-title'), html.Div(f"{format_compact(supply['max']).replace('₹ ', '')}" if supply['max'] else "∞", className='metric-value')]), html.Div(className='metric-box', children=[html.Div("Circulating", className='metric-title'), html.Div(f"{format_compact(supply['supply']).replace('₹ ', '')}", className='metric-value')])])]
    fig_candle = go.Figure(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00CC96', decreasing_line_color='#FF4136', name='Price')); df['SMA'] = df['close'].rolling(5).mean(); fig_candle.add_trace(go.Scatter(x=df['timestamp'], y=df['SMA'], line=dict(color='#2962ff', width=1.5), name='Trend')); fig_candle.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=0, r=50, t=10, b=30), yaxis=dict(gridcolor='rgba(255,255,255,0.05)', showgrid=True), xaxis=dict(gridcolor='rgba(255,255,255,0.05)', showgrid=False), hovermode='x unified', hoverlabel=dict(bgcolor="#1e1e1e", font_size=12, font_color="white", bordercolor="#333"))
    price_html = html.Span(f"{format_currency(latest_price)}", style={'color': color, 'textShadow': f'0 0 15px {color}80'})
    bar_x, bar_y, bar_colors = [], [], []
    for s in TRACKER_SYMBOLS:
        if s in tickers: t = tickers[s]; bar_x.append(SYMBOL_MAP.get(s, s)); bar_y.append(t['percentage']); bar_colors.append('#00CC96' if t['percentage'] >= 0 else '#FF4136')
    sorted_bars = sorted(zip(bar_x, bar_y, bar_colors), key=lambda x: x[1], reverse=True); 
    if sorted_bars: bar_x, bar_y, bar_colors = zip(*sorted_bars)
    fig_bar = go.Figure(go.Bar(x=bar_x, y=bar_y, marker_color=bar_colors, text=[f"{y:.2f}%" for y in bar_y], textposition='auto')); fig_bar.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=30, r=20, t=10, b=40), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), xaxis=dict(showgrid=False))
    title_suffix = "LIVE VIEW"; 
    if tf_data['tf'] == '15m': title_suffix = "24H VIEW"
    elif tf_data['tf'] == '1w': title_suffix = "LONG TERM"
    return fig_candle, price_html, metrics_html, fig_bar, f"{full_name} // {title_suffix}", tv_html

@app.callback([Output('markets-table-content', 'children'), Output('trending-content', 'children'), Output('news-content', 'children'), Output('dexscan-content', 'children'), Output('current-page-store', 'data'), Output('page-display', 'children'), Output('prev-btn', 'disabled'), Output('next-btn', 'disabled')], [Input('market-interval', 'n_intervals'), Input('prev-btn', 'n_clicks'), Input('next-btn', 'n_clicks')], [State('current-page-store', 'data')])
def update_market_trending_news_dex(n, prev_clicks, next_clicks, current_page):
    market_data = fetch_market_data(); ctx_id = ctx.triggered_id; 
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
        dex_cards.append(html.Div(className='dex-card', children=[html.Div(className='dex-header', style={'display':'flex','justifyContent':'space-between','marginBottom':'15px','color':'#fff','fontWeight':'bold'}, children=[html.Span(cat), html.Span(">", style={'color': '#666', 'fontSize': '0.9rem'})]), html.Div(rows)]))
    start_idx = (current_page - 1) * 10; end_idx = start_idx + 10; page_data = market_data[start_idx:end_idx]
    header = html.Tr([html.Th("#"), html.Th("ASSET"), html.Th("PRICE"), html.Th("MARKET CAP"), html.Th("VOLUME (24H)"), html.Th("CHANGE (24H)"), html.Th("7D %"), html.Th("TREND")]); rows = []
    for coin in page_data:
        col24 = 'positive' if coin['change_24h'] >= 0 else 'negative'; col7d = 'positive' if coin['change_7d'] >= 0 else 'negative'; spark_color = '#00CC96' if coin['change_7d'] >= 0 else '#FF4136'
        fig_spark = go.Figure(go.Scatter(y=coin['history'], mode='lines', line=dict(color=spark_color, width=2), fill='tozeroy', fillcolor=f"rgba({int(spark_color[1:3],16)}, {int(spark_color[3:5],16)}, {int(spark_color[5:7],16)}, 0.1)")); fig_spark.update_layout(template='plotly_dark', height=40, width=120, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        row = html.Tr([html.Td(coin['rank'], style={'color':'#666'}), html.Td(html.Div(className='coin-cell', children=[html.Img(src=get_icon_url(coin['symbol']), className='coin-icon'), html.Div([html.Div(coin['name'], style={'fontWeight': '600'}), html.Div(coin['symbol'].split('/')[0], style={'fontSize':'0.75rem', 'color':'#888'})])])), html.Td(format_currency(coin['price']), style={'fontWeight': '600', 'fontFamily':'monospace'}), html.Td(format_compact(coin['mkt_cap'])), html.Td(format_compact(coin['volume'])), html.Td(f"{coin['change_24h']:.2f}%", className=col24), html.Td(f"{coin['change_7d']:.2f}%", className=col7d), html.Td(dcc.Graph(figure=fig_spark, config={'staticPlot': True}), style={'padding':'0'})]); rows.append(row)
    table = html.Table([html.Thead(header), html.Tbody(rows)], className='crypto-table')
    gainers = sorted(market_data, key=lambda x: x['change_24h'], reverse=True)[:5]; losers = sorted(market_data, key=lambda x: x['change_24h'])[:5]
    def create_trend_list(items):
        rows = []
        for i, coin in enumerate(items): rows.append(html.Div(className='trending-row', style={'display':'flex','justifyContent':'space-between','padding':'12px 0','borderBottom':'1px solid #222'}, children=[html.Div(className='coin-cell', children=[html.Div(f"{i+1}", style={'color':'#666','width':'20px'}), html.Img(src=get_icon_url(coin['symbol']), className='coin-icon'), html.Div([html.Div(coin['name'], style={'fontWeight': 'bold'}), html.Div(format_currency(coin['price']), style={'fontSize':'0.85rem'})])]), html.Div(f"{coin['change_24h']:.2f}%", style={'color': '#00CC96' if coin['change_24h']>=0 else '#FF4136', 'fontWeight':'bold'})]))
        return rows
    trending_html = [html.Div(className='trending-card', children=[html.Div("🔥 TOP GAINERS", className='trending-header', style={'color': '#00CC96','fontWeight':'bold','marginBottom':'20px'}), html.Div(create_trend_list(gainers))]), html.Div(className='trending-card', children=[html.Div("📉 TOP LOSERS", className='trending-header', style={'color': '#FF4136','fontWeight':'bold','marginBottom':'20px'}), html.Div(create_trend_list(losers))])]
    news_items = generate_crypto_news(); news_cards = []
    for news in news_items: card = html.Div(className='news-card', children=[html.Img(src=news['image'], className='news-img'), html.Div(className='news-content', children=[html.Span(news['source'], style={'backgroundColor':'#2962ff','color':'white','padding':'2px 8px','borderRadius':'4px','fontSize':'0.7rem'}), html.Div(news['title'], style={'fontSize':'1.1rem','fontWeight':'bold','margin':'10px 0','lineHeight':'1.4'}), html.P(news['desc'], style={'color':'#aaa', 'fontSize':'0.9rem'}), html.Div(children=[html.Span(news['time']), html.A("Read More >", href="#", style={'color':'#00CC96', 'textDecoration':'none'})], style={'display':'flex','justifyContent':'space-between','color':'#666','fontSize':'0.8rem','marginTop':'15px'})])]); news_cards.append(card)
    return table, trending_html, news_cards, dex_cards, current_page, f"Page {current_page} of 10", (current_page == 1), (current_page == 10)

if __name__ == '__main__':
    app.run_server(debug=True) 
