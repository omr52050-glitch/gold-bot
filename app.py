import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

st.set_page_config(page_title="محلل الذهب", layout="wide", initial_sidebar_state="collapsed")

st.title("🏆 محلل الذهب الذكي (XAUUSD)")

timeframe = st.selectbox("اختر الإطار الزمني:", ["15m", "1h", "4h", "1d"], index=0)

@st.cache_data(ttl=60)
def load_data(tf):
    period = "1mo" if tf in ["15m", "1h"] else "1y"
    df = yf.download(tickers="GC=F", period=period, interval=tf)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    return df.dropna()

df = load_data(timeframe)
data_slice = df.tail(60)

last_row = df.iloc[-1]
close_p = float(last_row['Close'])
atr_v = float(last_row['ATR'])
is_bullish = float(last_row['EMA_50']) > float(last_row['EMA_200'])

# حساب المستويات بناءً على الاتجاه الحقيقي والسعر الحالي
if is_bullish:
    sl_price = close_p - (atr_v * 1.5)
    tp_price = close_p + ((close_p - sl_price) * 2.0)
    signal_type = "BUY"
else:
    sl_price = close_p + (atr_v * 1.5)
    tp_price = close_p - ((sl_price - close_p) * 2.0)
    signal_type = "SELL"

# عرض البطاقات التوضيحية للأهداف والستوب لوز
col1, col2, col3 = st.columns(3)
col1.metric("السعر الحالي", f"${close_p:.2f}")
col2.metric("الهدف المقترح (TP)", f"${tp_price:.2f}")
col3.metric("وقف الخسارة (SL)", f"${sl_price:.2f}")

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

# رسم خط الهدف (Take Profit)
fig.add_hline(
    y=tp_price, line_dash="dash", line_color="green", line_width=2,
    annotation_text=f"الهدف TP: {tp_price:.2f}", annotation_position="top right"
)

# رسم خط وقف الخسارة (Stop Loss)
fig.add_hline(
    y=sl_price, line_dash="dash", line_color="red", line_width=2,
    annotation_text=f"الوقف SL: {sl_price:.2f}", annotation_position="bottom right"
)

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=500,
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True)
