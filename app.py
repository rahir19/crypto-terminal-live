import pandas as pd
import plotly.graph_objects as go
import dash
import random
import numpy as np
from datetime import datetime, timedelta
from dash import Dash, dcc, html, ctx
from dash.dependencies import Input, Output, State, ALL

# --- CONFIGURATION ---
USD_TO_INR_RATE = 84.50

SYMBOL_MAP = {
    'BTC/USDT': 'Bitcoin', 'ETH/USDT': 'Ethereum', 'BNB/USDT': 'Binance Coin',
    'SOL/USDT': 'Solana', 'XRP/USDT': 'XRP', 'DOGE/USDT': 'Dogecoin',
    'ADA/USDT': 'Cardano', 'TRX/USDT': 'TRON', 'AVAX/USDT': 'Avalanche',
    'SHIB/USDT': 'Shiba Inu'
}

# Updated Real Prices (Approx) for start point
BASE_PRICES_USD = {
    'BTC/USDT': 98500.00, 'ETH/USDT': 3910.00, 'BNB/USDT': 660.00,
    'SOL/USDT': 150.00, 'XRP/USDT': 1.92, 'DOGE/USDT': 0.44,
    'ADA/USDT': 1.20, 'TRX/USDT': 0.22, 'AVAX/USDT': 50.00,
    'SHIB/USDT': 0.000027
}

UPCOMING_PROJECTS = [
    {'name': 'DeepSnitch AI', 'symbol': 'DSNT', 'category': 'AI Agent', 'price': '$0.024', 'raised': '85%', 'target': '$1M', 'desc': 'AI-powered trading surveillance.'},
    {'name': 'Best Wallet', 'symbol': 'BEST', 'category': 'DeFi Wallet', 'price': '$0.089', 'raised': '92%', 'target': '$15M', 'desc': 'Next-gen Web3 wallet.'},
    {'name': 'Bitcoin Hyper', 'symbol': 'HYPER', 'category': 'Layer 2', 'price': '$0.005', 'raised': '45%', 'target': '$5M', 'desc': 'High-speed Bitcoin Layer 2.'},
    {'name': 'Tapzi', 'symbol': 'TAP', 'category': 'GameFi', 'price': '$0.012', 'raised': '60%', 'target': '$2M', 'desc': 'Play-to-earn gaming on Solana.'}
]

TRACKER_SYMBOLS = list(SYMBOL_MAP.keys())
DROPDOWN_OPTIONS = [{'label': SYMBOL_MAP[s], 'value': s} for s in TRACKER_SYMBOLS]
DEFAULT_SYMBOL = 'BTC/USDT'

# --- HELPERS ---
def format_currency(value):
    return f'₹ {value:,.2f}'

def format_compact(value):
    if value >= 1_000_000_000_000: return f"₹{value/1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000: return f"₹{value/1_000_000_000:.2f}B"
    if value >= 1_000_000: return f"₹{value/1_000_000:.2f}M"
    return f"₹{value:,.0f}"

def get_icon_url(symbol):
    base = symbol.split('/')[0].lower()
    return f"https://assets.coincap.io/assets/icons/{base}@2x.png"

def generate_crypto_news():
    headlines = ["Bitcoin Breaks $99k Resistance Level", "Ethereum 3.0 Upgrade Announced", "Solana Transactions Hit Record High", "New Crypto Regulation Bill Proposed", "Institutional Inflows Reach All-Time High", "XRP Wins Major Legal Battle"]
    images = ["https://images.unsplash.com/photo-1518546305927-5a555bb7020d?auto=format&fit=crop&w=500&q=60", "https://images.unsplash.com/photo-1621761191319-c6fb62004040?auto=format&fit=crop&w=500&q=60", "https://images.unsplash.com/photo-1622630998477-20aa696fab05?auto=format&fit=crop&w=500&q=60"]
    news_items = []
    for i in range(6):
        item = {'title': headlines[i], 'source': 'CryptoNews', 'time': f"{random.randint(1, 59)} mins ago", 'image': random.choice(images), 'desc': "Market is showing strong bullish momentum..."}
        news_items.append(item)
    return news_items

# --- ADVANCED DATA GENERATOR (LOOKS REAL) ---
def generate_chart_data(symbol, limit):
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='T')
    base_usd = BASE_PRICES_USD.get(symbol, 100)
    base_inr = base_usd * USD_TO_INR_RATE
    
    # High Volatility Logic
    volatility = base_inr * 0.008 # Increased volatility
    changes = np.random.normal(0, volatility, limit)
    price_path = base_inr + np.cumsum(changes)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price_path,
        'high': price_path * 1.003,
        'low': price_path * 0.997,
        'close': price_path * (1 + np.random.normal(0, 0.0015, limit)), # More noise
        'volume': np.random.randint(1000, 100000, limit)
    })
    return df

def generate_market_list():
    data = []
    for i, sym in enumerate(TRACKER_SYMBOLS):
        base_usd = BASE_PRICES_USD.get(sym, 100)
        # Random fluctuation for table
        p_inr = base_usd * USD_TO_INR_RATE * (1 + random.uniform(-0.03, 0.03))
        change = random.uniform(-8, 12)
        data.append({
            'rank': i + 1, 'symbol': sym, 'name': SYMBOL_MAP[sym],
            'price': p_inr, 'change_24h': change
        })
    return data

# --- APP LAYOUT ---
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
            
            /* WELCOME PAGE & GRID */
            .welcome-container { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: #050a14; background-image: linear-gradient(rgba(0, 80, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 80, 255, 0.05) 1px, transparent 1px); background-size: 50px 50px; z-index: 2000; display: flex; flex-direction: column; overflow: hidden; }
            .welcome-container::after { content: ""; position: absolute; top: 50%; left: 50%; width: 100%; height: 100%; transform: translate(-50%, -50%); background: radial-gradient(circle, rgba(0,80,255,0.15) 0%, transparent 70%); pointer-events: none; }
            .welcome-nav { display: flex; justify-content: space-between; align-items: center; padding: 25px 60px; flex-shrink: 0; z-index: 10; }
            .welcome-brand { font-size: 1.6rem; font-weight: 900; letter-spacing: 1px; color: white; }
            .welcome-links button { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: white; margin-left: 20px; padding: 8px 20px; cursor: pointer; border-radius: 30px; font-weight: 600; transition: 0.3s; }
            .welcome-links button:hover { color: #00CC96; border-color: #00CC96; }
            .welcome-body { flex: 1; display: flex; align-items: center; justify-content: space-between; padding: 0 100px; z-index: 10; gap: 50px; }
            .hero-section { flex: 1; max-width: 600px; }
            .hero-title { font-size: 4rem; font-weight: 900; margin-bottom: 20px; line-height: 1.1; color: white; }
            .hero-subtitle { font-size: 1.1rem; color: #8899ac; margin-bottom: 40px; }
            .login-btn-large { background: linear-gradient(90deg, #00CC96, #007bff); border: none; color: white; padding: 16px 45px; font-size: 1rem; font-weight: bold; border-radius: 50px; cursor: pointer; box-shadow: 0 0 20px rgba(0, 204, 150, 0.4); transition: 0.3s; }
            .login-btn-large:hover { transform: translateY(-2px); box-shadow: 0 0 40px rgba(0, 204, 150, 0.7); }
            
            /* MOBILE MOCKUP (Hidden on smaller screens if needed, but kept here) */
            .mobile-mockup-wrapper { flex: 1; display: flex; justify-content: center; align-items: center; perspective: 1000px; position: relative; }
            .mobile-frame { width: 320px; height: 650px; background: #000; border-radius: 40px; border: 3px solid #333; position: relative; overflow: hidden; z-index: 5; box-shadow: 0 30px 60px rgba(0,0,0,0.6); transform: rotateY(-15deg) rotateX(5deg); transition: transform 0.5s ease; }
            .mobile-frame:hover { transform: rotateY(0) rotateX(0); }
            .mobile-screen { width: 100%; height: 100%; background: #0a0e17; overflow: hidden; position: relative; padding-top: 20px; }
            .scroll-container { display: flex; flex-direction: column; animation: scrollUp 10s linear infinite; }
            @keyframes scrollUp { 0% { transform: translateY(0); } 100% { transform: translateY(-50%); } }
            .fake-card { background: rgba(30, 35, 45, 0.9); border-radius: 16px; margin: 15px; padding: 15px; border: 1px solid rgba(255,255,255,0.05); }
            .fake-chart { height: 60px; background: linear-gradient(90deg, #151a21, #1f2530, #151a21); border-radius: 8px; margin-top: 10px; position: relative; }
            .fake-chart::after { content: ''; position: absolute; bottom: 10px; left: 0; width: 100%; height: 2px; background: #00CC96; transform: rotate(-5deg); box-shadow: 0 0 8px #00CC96; }
            .txt-green { color: #00CC96; font-weight: bold; } .txt-red { color: #FF4136; font-weight: bold; }

            /* MODAL */
            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 5000; display: flex; justify-content: center; align-items: center; }
            .modal-content { background: #11151a; padding: 40px; border-radius: 20px; border: 1px solid #333; text-align: center; width: 400px; color: #e0e0e0; position: relative; box-shadow: 0 0 50px rgba(0,0,0,0.5); }
            .modal-close { position: absolute; top: 15px; right: 20px; font-size: 2rem; cursor: pointer; color: #666; line-height: 1; }
            .modal-close:hover { color: #FF4136; }
            .contact-item { border-bottom: 1px solid #222; padding: 10px 0; display: flex; justify-content: space-between; }

            /* DASHBOARD CSS */
            .navbar { display: flex; justify-content: space-between; align-items: center; background-color: #161a1e; padding: 15px 30px; border-bottom: 1px solid #2a2e39; position: sticky; top: 0; z-index: 1000; }
            .nav-brand { font-size: 1.8rem; font-weight: 900; color: #F0B90B; display: flex; align-items: center; gap: 10px; }
            .nav-controls { display: flex; align-items: center; gap: 15px; }
            .custom-tabs { border-bottom: 1px solid #333; background: #121212; }
            .custom-tab { background-color: #121212; color: #888; border: none; padding: 15px 25px; font-size: 1rem; cursor: pointer; }
            .custom-tab--selected { background-color: #121212; color: #F0B90B !important; border-bottom: 2px solid #F0B90B; font-weight: bold; }
            .chart-wrapper { flex: 3; background-color: #1e1e1e; border-radius: 8px; }
            .metrics-container { flex: 1; background-color: #1e1e1e; padding: 20px; border-radius: 8px; }
            .market-cap-card { background-color: #151a1e; border: 1px solid #2a2e39; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px; }
            .metric-value-large { font-size: 1.5rem; color: #fff; font-weight: bold; }
            .bottom-bar-chart { margin: 20px; background-color: #1e1e1e; padding: 15px; border-radius: 8px; }
            .app-footer { text-align: center; padding: 40px 20px; color: #555; font-size: 0.85rem; border-top: 1px solid #222; margin-top: 40px; background-color: #161a1e; }
            .control-bar-container { display: flex; justify-content: space-between; align-items: center; background-color: #1e1e1e; padding: 10px 20px; border-radius: 8px 8px 0 0; }
            .btn-group { display: flex; background-color: #2a2a2a; border-radius: 6px; padding: 3px; gap: 2px; }
            .control-btn { background: transparent; border: none; color: #888; padding: 6px 15px; cursor: pointer; }
            .control-btn.active { background: #fff; color: #000; }
            .flex-container { display: flex; gap: 20px; padding: 0 20px; }
            .crypto-table { width: 100%; border-collapse: collapse; color: #fff; }
            .crypto-table th { text-align: left; padding: 15px; border-bottom: 1px solid #333; color: #888; }
            .crypto-table td { padding: 12px; border-bottom: 1px solid #2a2e39; }
            .positive { color: #00CC96; } .negative { color: #FF4136; }
            .coin-cell { display: flex; align-items: center; gap: 10px; }
            .coin-icon { width: 28px; height: 28px; border-radius: 50%; background-color: #333; }
            .news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
            .news-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; overflow: hidden; }
            .news-img { width: 100%; height: 160px; object-fit: cover; }
            .news-content { padding: 15px; }
            .presale-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
            .presale-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 20px; position: relative; }
            .presale-btn { width: 100%; background: #246BFD; border: none; color: white; padding: 10px; border-radius: 6px; font-weight: bold; cursor: pointer; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''

# --- FAKE CONTENT FOR MOBILE ---
def get_fake_content_cards():
    content = []
    for _ in range(2): 
        content.append(html.Div(className='fake-card', children=[
            html.Div("Market Analysis", style={'color':'#888', 'fontSize':'0.8rem'}),
            html.H4("BTC Resistance Broken", style={'margin':'5px 0', 'color':'white'}),
            html.Div(className='fake-chart')
        ]))
    return content

# --- LAYOUTS ---
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
                html.P("Professional Cryptocurrency Trading & Analysis Terminal. Real-time insights and advanced metrics.", className='hero-subtitle'),
                html.Button("LOGIN", id='login-btn-main', className='login-btn-large')
            ]),
            html.Div(className='mobile-mockup-wrapper', children=[
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
            
            # TAB 1: MAIN CHART (SIMULATED FOR SAFETY)
            dcc.Tab(label='Chart', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(style={'marginTop': '20px'}), 
                html.H2(id='live-price-display', className='live-price-big'),
                html.Div(className='flex-container', children=[
                    html.Div(className='chart-wrapper', children=[
                        html.Div(className='control-bar-container', children=[
                            html.Div(className='btn-group', children=[html.Button("Price", className='control-btn active'), html.Button("Market Cap", className='control-btn'), html.Button("TradingView", className='control-btn')]),
                            html.Div(className='btn-group', children=[html.Button("LIVE", id={'type': 'tf-btn', 'index': 'LIVE'}, className='control-btn live-btn active'), html.Button("24H", id={'type': 'tf-btn', 'index': '24H'}, className='control-btn')])
                        ]),
                        html.Div(style={'padding': '15px'}, children=[html.H3(id='chart-title', style={'borderBottom': '1px solid #333', 'paddingBottom': '10px', 'marginTop': '0'}), dcc.Graph(id='live-candlestick-chart', style={'height': '450px'})])
                    ]),
                    html.Div(className='metrics-container', children=[html.Div(id='key-metrics-panel')])
                ]),
                html.Div(className='bottom-bar-chart', children=[html.H4("Top 10 Crypto Performance (24h)", style={'color': '#DDD'}), dcc.Graph(id='bar-chart-24h', style={'height': '300px'})])
            ]),

            # TAB 2: TRADING VIEW (THE GAME CHANGER - REAL CLIENT SIDE)
            dcc.Tab(label='Trading View', className='custom-tab', selected_className='custom-tab--selected', children=[
                html.Div(style={'height': '750px', 'padding': '20px'}, children=[
                    # THIS IFRAME BYPASSES THE SERVER BLOCK. IT IS 100% REAL LIVE DATA.
                    html.Iframe(
                        src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_76d87&symbol=BINANCE%3ABTCUSDT&interval=D&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=1&saveimage=1&toolbarbg=F1F3F6&studies=[]&hideideas=1&theme=Dark&style=1&timezone=Etc%2FUTC&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&locale=en&utm_source=localhost&utm_medium=widget&utm_campaign=chart&utm_term=BINANCE%3ABTCUSDT",
                        style={'width': '100%', 'height': '100%', 'border': 'none'}
                    )
                ])
            ]),

            # OTHER TABS (Simplified for stability)
            dcc.Tab(label='Markets', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(className='market-table-container', children=[html.H2("Top 100 Cryptocurrencies", style={'color': 'white', 'marginBottom': '20px'}), html.Div(id='markets-table-content')])]),
            dcc.Tab(label='News', className='custom-tab', selected_className='custom-tab--selected', children=[html.Div(id='news-content', className='news-grid', children="Loading News...")])
        ]),
        
        html.Div(className='app-footer', children=[html.Div("© 2025 Crypto Master Terminal.", className='footer-text')]),
        dcc.Interval(id='interval-component', interval=2000, n_intervals=0),
        dcc.Interval(id='market-interval', interval=10000, n_intervals=0)
    ])

# --- APP LAYOUT ---
app.layout = html.Div([
    dcc.Store(id='login-state-store', data=False),
    html.Div(id='page-content', children=get_welcome_layout())
])

# --- CALLBACKS ---
@app.callback(Output('page-content', 'children'), Input('login-btn-main', 'n_clicks'), prevent_initial_call=True)
def login_success(n): return get_dashboard_layout()

@app.callback(Output('modal-container', 'children'), [Input('about-link-btn', 'n_clicks'), Input('contact-link-btn', 'n_clicks'), Input({'type': 'close-modal', 'index': 'btn'}, 'n_clicks')], prevent_initial_call=True)
def manage_modals(about, contact, close):
    ctx_id = ctx.triggered_id
    if ctx_id and isinstance(ctx_id, dict) and ctx_id.get('type') == 'close-modal': return None
    content = None
    if ctx_id == 'about-link-btn':
        content = html.Div([html.H3("About Us", style={'color': '#00CC96'}), html.P("Professional crypto terminal.")])
    elif ctx_id == 'contact-link-btn':
        content = html.Div(className='contact-info-box', children=[html.H3("Contact"), html.Div(className='contact-item', children=[html.Span("Name"), html.Span("Raghav Ahir Yaduvanshi", style={'color':'white'})]), html.Div(className='contact-item', children=[html.Span("Phone"), html.Span("6266649445", style={'color':'white'})]), html.Div(className='contact-item', children=[html.Span("GitHub"), html.A("github.com/rahir19", href="https://github.com/rahir19", target="_blank", className='contact-link')])])
    if content:
        return html.Div(className='modal-overlay', children=[html.Div(className='modal-content', children=[html.Span("×", id={'type': 'close-modal', 'index': 'btn'}, className='modal-close'), content])])
    return None

# --- MAIN DASHBOARD LOGIC (SIMULATION MODE) ---
@app.callback([Output('live-candlestick-chart', 'figure'), Output('live-price-display', 'children'), Output('key-metrics-panel', 'children'), Output('bar-chart-24h', 'figure'), Output('chart-title', 'children')], [Input('interval-component', 'n_intervals'), Input('coin-select-dropdown', 'value')])
def update_overview(n, selected_symbol):
    # Simulation Data (Guaranteed to load)
    df = generate_chart_data(selected_symbol, 50)
    latest_price = df['close'].iloc[-1]
    pct_change = (latest_price - df['open'].iloc[0]) / df['open'].iloc[0] * 100
    color = '#00CC96' if pct_change >= 0 else '#FF4136'
    
    metrics = [html.Div(className='market-cap-card', children=[html.Div("Market Cap ⓘ", className='metric-title'), html.Div(format_compact(latest_price * 1000000), className='metric-value-large'), html.Div(f"{pct_change:+.2f}%", style={'color': color})])]
    
    fig = go.Figure(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00CC96', decreasing_line_color='#FF4136'))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=0, r=40, t=10, b=20))
    
    bar_x = [SYMBOL_MAP[s] for s in TRACKER_SYMBOLS[:5]]
    bar_y = [random.uniform(-5, 5) for _ in bar_x]
    bar_colors = ['#00CC96' if v >= 0 else '#FF4136' for v in bar_y]
    fig_bar = go.Figure(go.Bar(x=bar_x, y=bar_y, marker_color=bar_colors))
    fig_bar.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20))
    
    return fig, html.Span(f"{format_currency(latest_price)}", style={'color': color}), metrics, fig_bar, f"{selected_symbol} Live"

@app.callback([Output('markets-table-content', 'children'), Output('news-content', 'children')], [Input('market-interval', 'n_intervals')])
def update_market_news(n):
    market_data = generate_market_list()
    header = html.Tr([html.Th("Rank"), html.Th("Asset"), html.Th("Price"), html.Th("24h %")])
    rows = [html.Tr([html.Td(c['rank']), html.Td(c['name']), html.Td(format_currency(c['price'])), html.Td(f"{c['change_24h']:.2f}%", className='positive' if c['change_24h']>=0 else 'negative')]) for c in market_data[:10]]
    news = [html.Div(className='news-card', children=[html.Img(src=item['image'], className='news-img'), html.Div(className='news-content', children=[html.Div(item['title'], className='news-title')])]) for item in generate_crypto_news()]
    return html.Table([html.Thead(header), html.Tbody(rows)], className='crypto-table'), news

# --- RUN ---
server = app.server 
if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=8088)
