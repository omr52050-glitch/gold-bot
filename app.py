import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

# إعدادات الصفحة والتصميم للجوال
st.set_page_config(page_title="منصة التحليل الذكي", layout="wide", initial_sidebar_state="collapsed")

st.title("⚡ منصة التحليل الفني الذكي")

# القوائم العلوية لاختيار رمز التداول والفريم الزمني
col_symbol, col_tf = st.columns(2)

with col_symbol:
    asset = st.selectbox("اختر زوج التداول:", ["الذهب (XAUUSD)", "البتكوين (BTCUSD)"])

with col_tf:
    timeframe = st.selectbox("الإطار الزمني:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)

# تحديد الرمز البرمجي والفترة المناسبة للجلب
ticker_symbol = "GC=F" if asset == "الذهب (XAUUSD)" else "BTC-USD"

@st.cache_data(ttl=15)
def load_data(symbol, tf):
    # الفريمات السريعة (1m و 5m) تتطلب فترة جلب قصيرة جداً في yfinance
    if tf == "1m":
        period = "7d"
    elif tf in ["5m", "15m"]:
        period = "1mo"
    else:
        period = "1y"
        
    df = yf.download(tickers=symbol, period=period, interval=tf)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # حساب المؤشرات الفنية
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    return df.dropna()

df = load_data(ticker_symbol, timeframe)
data_slice = df.tail(60)

last_row = df.iloc[-1]
close_p = float(last_row['Close'])
atr_v = float(last_row['ATR'])
is_bullish = float(last_row['EMA_50']) > float(last_row['EMA_200'])

# حساب مستويات الأهداف والوقف بناءً على اتجاه السوق والتقلب
if is_bullish:
    sl_price = close_p - (atr_v * 1.5)
    tp_price = close_p + ((close_p - sl_price) * 2.0)
    trend_text = "اتجاه صاعد (صفقات شراء)"
else:
    sl_price = close_p + (atr_v * 1.5)
    tp_price = close_p - ((sl_price - close_p) * 2.0)
    trend_text = "اتجاه هابط (صفقات بيع)"

# عرض البيانات الرقمية بشكل واضح ومبسط
st.markdown(f"### 📊 حالة السوق: **{trend_text}**")
col1, col2, col3 = st.columns(3)
col1.metric("السعر الحالي", f"${close_p:,.2f}")
col2.metric("الهدف (TP)", f"${tp_price:,.2f}")
col3.metric("الوقف (SL)", f"${sl_price:,.2f}")

# رسم الشارت التفاعلي
fig = go.Figure()

# إضافة الشموع اليابانية
fig.add_trace(go.Candlestick(
    x=data_slice.index,
    open=data_slice['Open'], high=data_slice['High'],
    low=data_slice['Low'], close=data_slice['Close'],
    name="السعر"
))

# إضافة المتوسطات
fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_50'], name="EMA 50", line=dict(color='cyan', width=1)))
fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_200'], name="EMA 200", line=dict(color='orange', width=1)))

# خط الهدف (Take Profit)
fig.add_hline(
    y=tp_price, line_dash="dash", line_color="green", line_width=2,
    annotation_text=f"الهدف: {tp_price:,.2f}", annotation_position="top right"
)

# خط وقف الخسارة (Stop Loss)
fig.add_hline(
    y=sl_price, line_dash="dash", line_color="red", line_width=2,
    annotation_text=f"الوقف: {sl_price:,.2f}", annotation_position="bottom right"
)

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=500,
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True)
