import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

# إعدادات الصفحة
st.set_page_config(page_title="منصة التحليل الرقمي الذكي", layout="wide", initial_sidebar_state="collapsed")

st.title("⚡ منصة التحليل الفني المتقدم (السعر الفوري)")

# القوائم العلوية
col_symbol, col_tf = st.columns(2)

with col_symbol:
    asset = st.selectbox("اختر زوج التداول:", ["الذهب الفوري (XAUUSD)", "البتكوين (BTCUSD)"])

with col_tf:
    timeframe = st.selectbox("الإطار الزمني:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)

ticker_symbol = "XAUUSD=X" if asset == "الذهب الفوري (XAUUSD)" else "BTC-USD"

@st.cache_data(ttl=10)
def load_data(symbol, tf):
    period = "7d" if tf in ["1m", "5m"] else ("1mo" if tf == "15m" else "1y")
    df = yf.download(tickers=symbol, period=period, interval=tf, progress=False)
    
    # معالجة مشكلة MultiIndex في yfinance بشكل كامل
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # التأكد من تحويل السلاسل إلى مسلسلات أرقام أحادية
    close_series = df['Close'].squeeze()
    high_series = df['High'].squeeze()
    low_series = df['Low'].squeeze()

    if len(df) < 50:
        return None

    # حساب المؤشرات بأمان
    df['EMA_50'] = ta.trend.ema_indicator(close_series, window=50)
    df['EMA_200'] = ta.trend.ema_indicator(close_series, window=200)
    df['RSI'] = ta.momentum.rsi(close_series, window=14)
    
    macd = ta.trend.MACD(close_series)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    df['ATR'] = ta.volatility.average_true_range(high_series, low_series, close_series, window=14)
    
    return df.dropna()

df = load_data(ticker_symbol, timeframe)

if df is None or df.empty:
    st.error("⚠️ تعذر جلب البيانات لهذا الفريم حالياً، يرجى اختيار إطار زمني آخر أو الانتظار لثوانٍ.")
else:
    data_slice = df.tail(60)
    last_row = df.iloc[-1]
    
    close_p = float(last_row['Close'])
    atr_v = float(last_row['ATR'])

    # تحديد الاتجاه
    is_bullish = (float(last_row['EMA_50']) > float(last_row['EMA_200'])) and (float(last_row['RSI']) >= 50)

    # حساب الستوب والأهداف الـ 5
    targets = []
    if is_bullish:
        trend_status = "🚀 اتجاه صاعد (فرصة شراء)"
        sl_price = close_p - (atr_v * 1.5)
        sl_pct = ((sl_price - close_p) / close_p) * 100
        
        for i in range(1, 6):
            tp = close_p + (atr_v * (1.0 * i))
            pct = ((tp - close_p) / close_p) * 100
            targets.append((f"الهدف {i} (TP{i})", tp, pct))
    else:
        trend_status = "🔻 اتجاه هابط (فرصة بيع)"
        sl_price = close_p + (atr_v * 1.5)
        sl_pct = ((sl_price - close_p) / close_p) * 100
        
        for i in range(1, 6):
            tp = close_p - (atr_v * (1.0 * i))
            pct = ((tp - close_p) / close_p) * 100
            targets.append((f"الهدف {i} (TP{i})", tp, pct))

    # ملخص حالة السوق
    st.markdown(f"### 📢 حالة السوق: **{trend_status}**")
    st.markdown(f"**السعر الفوري الحالي:** `${close_p:,.2f}` | **وقف الخسارة (SL):** `${sl_price:,.2f}` (`{sl_pct:+.2f}%`)")

    # بطاقات الأهداف الـ 5
    st.markdown("#### 🎯 الأهداف المتوقعة ونسبة التغير المئوية:")
    cols = st.columns(5)
    for idx, (name, val, pct) in enumerate(targets):
        cols[idx].metric(name, f"${val:,.2f}", f"{pct:+.2f}%")

    # الرسم البياني التفاعلي
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=data_slice.index,
        open=data_slice['Open'], high=data_slice['High'],
        low=data_slice['Low'], close=data_slice['Close'],
        name="السعر الفوري"
    ))

    fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_50'], name="EMA 50", line=dict(color='cyan', width=1)))
    fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_200'], name="EMA 200", line=dict(color='orange', width=1)))

    fig.add_hline(
        y=sl_price, line_dash="solid", line_color="red", line_width=2,
        annotation_text=f"الوقف (SL): {sl_price:,.2f} ({sl_pct:+.2f}%)", annotation_position="bottom right"
    )

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
    
