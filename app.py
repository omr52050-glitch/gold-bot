import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# ==========================================
# 1. تهيئة وإعدادات الصفحة للهاتف المحمول
# ==========================================
st.set_page_config(
    page_title="محلل الذهب والبيتكوين",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# تخصيص التصميم والواجهة لتناسب شاشات الهواتف (CSS)
st.markdown("""
    <style>
    body { direction: rtl; text-align: right; }
    .main .block-container { padding: 1rem 0.8rem; }
    .signal-buy {
        background-color: #132e21; border-right: 5px solid #26a69a;
        padding: 12px; border-radius: 8px; color: #26a69a; font-weight: bold;
    }
    .signal-sell {
        background-color: #3b1c21; border-right: 5px solid #ef5350;
        padding: 12px; border-radius: 8px; color: #ef5350; font-weight: bold;
    }
    .signal-neutral {
        background-color: #2a2e39; border-right: 5px solid #787b86;
        padding: 12px; border-radius: 8px; color: #b2b5be;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إعداد الأصول الماليّة
# ==========================================
ASSETS = {
    "الذهب (XAUUSD)": {"symbol": "GC=F", "min_atr": 1.5, "atr_sl_mult": 2.0, "atr_tp_mult": 4.0},
    "البيتكوين (BTCUSD)": {"symbol": "BTC-USD", "min_atr": 150.0, "atr_sl_mult": 1.5, "atr_tp_mult": 3.0}
}

# ==========================================
# 3. دالة جلب البيانات مع التخزين المؤقت
# ==========================================
@st.cache_data(ttl=60)
def load_market_data(symbol, period="1mo", interval="1h"):
    df = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

    # المتوسطات والمؤشرات
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()

    return df

# ==========================================
# 4. الشريط الجانبي والرئيسية
# ==========================================
st.sidebar.title("⚙️ الخيارات")
selected_asset_name = st.sidebar.selectbox("اختر أصل التحليل", list(ASSETS.keys()))
timeframe = st.sidebar.selectbox("الإطار الزمني", ["15m", "1h", "4h"], index=1)

st.title("📊 محلل الأسواق الذكي")
config = ASSETS[selected_asset_name]
df = load_market_data(config['symbol'], interval=timeframe)

if df is not None:
    latest, prev = df.iloc[-1], df.iloc[-2]
    close_price, prev_close = float(latest['Close']), float(prev['Close'])
    change = close_price - prev_close
    pct_change = (change / prev_close) * 100
    rsi_val, atr_val = float(latest['RSI']), float(latest['ATR'])
    ema9, ema21, ema200 = float(latest['EMA_9']), float(latest['EMA_21']), float(latest['EMA_200'])

    # عرض الأسعار
    col1, col2, col3 = st.columns(3)
    col1.metric("السعر الحالي", f"${close_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
    col2.metric("RSI", f"{rsi_val:.1f}")
    col3.metric("ATR", f"{atr_val:.2f}")

    # فحص الإشارة
    is_bullish, is_bearish = close_price > ema200, close_price < ema200
    is_volatile = atr_val >= config['min_atr']

    signal = "NEUTRAL"
    if (prev['EMA_9'] < prev['EMA_21']) and (ema9 > ema21) and is_bullish and (50 < rsi_val < 70) and is_volatile:
        signal = "BUY"
    elif (prev['EMA_9'] > prev['EMA_21']) and (ema9 < ema21) and is_bearish and (30 < rsi_val < 50) and is_volatile:
        signal = "SELL"

    st.subheader("📡 حالة الإشارة")
    if signal == "BUY":
        sl = round(close_price - (atr_val * config['atr_sl_mult']), 2)
        tp = round(close_price + (atr_val * config['atr_tp_mult']), 2)
        st.markdown(f'<div class="signal-buy">🟢 <b>إشارة شراء (BUY)</b><br>• الدخول: ${close_price:,.2f}<br>• SL: ${sl:,.2f}<br>• TP: ${tp:,.2f}</div>', unsafe_allow_html=True)
    elif signal == "SELL":
        sl = round(close_price + (atr_val * config['atr_sl_mult']), 2)
        tp = round(close_price - (atr_val * config['atr_tp_mult']), 2)
        st.markdown(f'<div class="signal-sell">🔴 <b>إشارة بيع (SELL)</b><br>• الدخول: ${close_price:,.2f}<br>• SL: ${sl:,.2f}<br>• TP: ${tp:,.2f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-neutral">⚪ <b>لا توجد إشارة تداول حالياً</b></div>', unsafe_allow_html=True)

    # رسم الشارت
    st.subheader("📈 الشارت التفاعلي")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="السعر"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], line=dict(color='#2962FF', width=1.5), name="EMA 9"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], line=dict(color='#FF6D00', width=1.5), name="EMA 21"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='#E91E63', width=2), name="EMA 200"))

    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
