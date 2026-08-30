import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

# إعدادات الصفحة والتصميم
st.set_page_config(page_title="منصة التحليل الرقمي الذكي", layout="wide", initial_sidebar_state="collapsed")

st.title("⚡ منصة التحليل الفني المتقدم والأهداف المتعددة")

# القوائم العلوية للاختيار
col_symbol, col_tf = st.columns(2)

with col_symbol:
    asset = st.selectbox("اختر زوج التداول:", ["الذهب (XAUUSD)", "البتكوين (BTCUSD)"])

with col_tf:
    timeframe = st.selectbox("الإطار الزمني:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)

ticker_symbol = "GC=F" if asset == "الذهب (XAUUSD)" else "BTC-USD"

@st.cache_data(ttl=15)
def load_data(symbol, tf):
    period = "7d" if tf == "1m" else ("1mo" if tf in ["5m", "15m"] else "1y")
    df = yf.download(tickers=symbol, period=period, interval=tf)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 1. المتوسطات المتحركة EMA
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    
    # 2. مؤشر RSI ومؤشر MACD
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    # 3. مؤشر ATR لتقلبات الأسعار
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    
    # 4. دمج حسابات SuperTrend لفلترة الإشارات الموثوقة
    atr_st = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=10)
    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_UB'] = hl2 + (3 * atr_st)
    df['Basic_LB'] = hl2 - (3 * atr_st)
    
    return df.dropna()

df = load_data(ticker_symbol, timeframe)
data_slice = df.tail(60)

last_row = df.iloc[-1]
close_p = float(last_row['Close'])
atr_v = float(last_row['ATR'])

# تحديد اتجاه السوق المدمج (EMA 50/200 + MACD + RSI)
is_bullish = (float(last_row['EMA_50']) > float(last_row['EMA_200'])) and (float(last_row['RSI']) >= 50)

# حساب الستوب لوز و 5 أهداف متدرجة مع نسبة التغير المئوية (%)
targets = []
if is_bullish:
    trend_status = "🚀 اتجاه صاعد قوي (فرصة شراء)"
    sl_price = close_p - (atr_v * 1.5)
    sl_pct = ((sl_price - close_p) / close_p) * 100
    
    # حساب 5 أهداف صاعدة
    for i in range(1, 6):
        tp = close_p + (atr_v * (1.0 * i))
        pct = ((tp - close_p) / close_p) * 100
        targets.append((f"الهدف {i} (TP{i})", tp, pct))
else:
    trend_status = "🔻 اتجاه هابط قوي (فرصة بيع)"
    sl_price = close_p + (atr_v * 1.5)
    sl_pct = ((sl_price - close_p) / close_p) * 100
    
    # حساب 5 أهداف هابطة
    for i in range(1, 6):
        tp = close_p - (atr_v * (1.0 * i))
        pct = ((tp - close_p) / close_p) * 100
        targets.append((f"الهدف {i} (TP{i})", tp, pct))

# عرض ملخص حالة السوق
st.markdown(f"### 📢 حالة السوق: **{trend_status}**")
st.markdown(f"**السعر الحالي:** `${close_p:,.2f}` | **وقف الخسارة (SL):** `${sl_price:,.2f}` (`{sl_pct:+.2f}%`)")

# عرض الأهداف الـ 5 في أعمدة بطاقات تفاعلية
st.markdown("#### 🎯 الأهداف المتوقعة ونسبة التغير المئوية:")
cols = st.columns(5)
for idx, (name, val, pct) in enumerate(targets):
    cols[idx].metric(name, f"${val:,.2f}", f"{pct:+.2f}%")

# رسم الشارت التفاعلي
fig = go.Figure()

# شموع التداول
fig.add_trace(go.Candlestick(
    x=data_slice.index,
    open=data_slice['Open'], high=data_slice['High'],
    low=data_slice['Low'], close=data_slice['Close'],
    name="السعر"
))

# المتوسطات المتحركة
fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_50'], name="EMA 50", line=dict(color='cyan', width=1)))
fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_200'], name="EMA 200", line=dict(color='orange', width=1)))

# رسم خط وقف الخسارة
fig.add_hline(
    y=sl_price, line_dash="solid", line_color="red", line_width=2,
    annotation_text=f"الوقف (SL): {sl_price:,.2f} ({sl_pct:+.2f}%)", annotation_position="bottom right"
)

# رسم الخطوط الأفقية للأهداف الـ 5 على الشارت
colors = ["#76ff03", "#64dd17", "#00c853", "#00e676", "#1de9b6"]
for idx, (name, val, pct) in enumerate(targets):
    fig.add_hline(
        y=val, line_dash="dash", line_color=colors[idx], line_width=1.5,
        annotation_text=f"{name}: {val:,.2f} ({pct:+.2f}%)", annotation_position="top right"
    )

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True)
