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


# FORMATTING FUNCTIONS
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


# EXCHANGE DATA FETCHERS
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
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col] * USD_TO_INR_RATE
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
            
            base_coin = symbol.split('/')[0]
            data.append({'rank': i + 1, 'symbol': symbol, 'name': base_coin, 'price': price,
                         'mkt_cap': mkt_cap, 'volume': volume,
                         'change_24h': change_24h,
                         'change_7d': change_24h * 3.2,
                         'history': history})
    except:
        pass
    return data


def calculate_cycle_indicators(df):
    if df is None or len(df) < 20:
        return None, 0, 0, 0

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
    if btc_df is None:
        return None
    btc_supply = 19_600_000
    btc_df = btc_df.bfill().ffill()
    total_mkt_cap = btc_df['close'] * btc_supply * 2.0
    total_volume = btc_df['volume'] * 10000 * 5
    return btc_df['timestamp'], total_mkt_cap, total_volume


# --- APP INITIALIZATION ---
app = Dash(__name__, title="Crypto Master", suppress_callback_exceptions=True)
server = app.server


# --- CSS (unchanged) ---
app.index_string = '''<!DOCTYPE html> ... (your long CSS stays same here) ... '''


# --- LOGIN PAGE LAYOUT ---
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
    html.Div(id='about-modal', className='modal-overlay', children=[html.Div(className='modal-content', children=[html.Button("×", id='close-about', className='close-modal'), html.H2("About Crypto Master", style={'color': '#fff', 'marginBottom': '15px'}), html.P("Crypto Master is a state-of-the-art dashboard built with Python and Dash.", style={'color': '#ccc', 'lineHeight': '1.6'})])]),
    html.Div(id='contact-modal', className='modal-overlay', children=[html.Div(className='modal-content', children=[html.Button("×", id='close-contact', className='close-modal'), html.H2("Contact Me", style={'color': '#fff', 'marginBottom': '25px'}), html.Div("Raghav Ahir Yaduvanshi"), html.Div("6266649445")])])
])


# --- DASHBOARD PAGE LAYOUT ---
dashboard_layout = html.Div([
    dcc.Store(id='timeframe-store', data={'tf': '1m', 'limit': 50}),
    dcc.Store(id='current-page-store', data=1),

    # HEADER UPDATED WITH REFRESH + LOGOUT BUTTONS
    html.Div([
        html.Div("⚡CRYPTO MASTER", className='header-title', style={'flex': '1'}),
        html.Div([
            html.Button("Refresh", id="refresh-btn", className="page-btn", style={'marginRight': '10px'}),
            html.Button("Logout", id="logout-btn", className="page-btn")
        ], style={'position': 'absolute', 'right': '30px', 'top': '25px'})
    ], style={'position': 'relative'}),

    dcc.Tabs(... your tabs remain unchanged ...)
])

# --- INITIAL APP LAYOUT ---
app.layout = html.Div([
    dcc.Store(id='login-state', data=False),
    html.Div(id='page-content', children=login_layout)
])


# --- LOGIN CALLBACK ---
@app.callback(
    [Output('page-content', 'children'), Output('login-error', 'children')],
    [Input('login-button', 'n_clicks')],
    [State('username-box', 'value'), State('password-box', 'value'), State('login-state', 'data')],
    prevent_initial_call=False
)
def manage_login(n_clicks, username, password, is_logged_in):
    if n_clicks is None:
        return no_update, no_update
    if username == "admin" and password == "admin":
        return dashboard_layout, ""
    return login_layout, "Invalid Credentials (Try: admin/admin)"


# --- LOGOUT BUTTON CALLBACK ---
@app.callback(
    Output('page-content', 'children'),
    Input('logout-btn', 'n_clicks'),
    prevent_initial_call=True
)
def logout_user(n):
    return login_layout


# --- REFRESH BUTTON CALLBACK (Client Side) ---
app.clientside_callback(
    """
    function(n) {
        if (n) {
            location.reload();
        }
        return null;
    }
    """,
    Output('refresh-btn', 'n_clicks'),
    Input('refresh-btn', 'n_clicks')
)


# --- REST OF EXISTING CALLBACKS (UNCHANGED) ---
# keep your entire callback code here (no need to modify anything)


if __name__ == '__main__':
    app.run_server(debug=True)
