import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

st.set_page_config(page_title="منصة التحليل الرقمي الذكي", layout="wide", initial_sidebar_state="collapsed")

st.title("⚡ منصة التحليل الفني المتقدم")

col_symbol, col_tf = st.columns(2)

with col_symbol:
    asset = st.selectbox("اختر زوج التداول:", ["الذهب (XAUUSD)", "البتكوين (BTCUSD)"])

with col_tf:
    timeframe = st.selectbox("الإطار الزمني:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)

# رموز تداول موثوقة ومستقرة دائماً في yfinance
ticker_symbol = "GC=F" if asset == "الذهب (XAUUSD)" else "BTC-USD"

@st.cache_data(ttl=15)
def load_data(symbol, tf):
    # تحديد فترة التنزيل بمرونة لتجنب الجداول الفارغة
    if tf == "1m":
        period = "5d"
    elif tf in ["5m", "15m"]:
        period = "1mo"
    elif tf in ["1h", "4h"]:
        period = "2mo"
    else:
        period = "1y"

    try:
        df = yf.Ticker(symbol).history(period=period, interval=tf)
        if df.empty:
            return None
        
        # تنظيف أسطر الجداول
        df = df.reset_index()
        
        # استخراج الأعمدة كـ Series ناعمة
        close_series = pd.Series(df['Close'].values, dtype='float64')
        high_series = pd.Series(df['High'].values, dtype='float64')
        low_series = pd.Series(df['Low'].values, dtype='float64')

        # حساب المؤشرات الفنية
        df['EMA_50'] = ta.trend.ema_indicator(close_series, window=50)
        df['EMA_200'] = ta.trend.ema_indicator(close_series, window=200)
        df['RSI'] = ta.momentum.rsi(close_series, window=14)
        
        macd = ta.trend.MACD(close_series)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        
        df['ATR'] = ta.volatility.average_true_range(high_series, low_series, close_series, window=14)
        
        return df.dropna()
    except Exception:
        return None

df = load_data(ticker_symbol, timeframe)

if df is None or len(df) < 10:
    st.warning("⚠️ يتم الآن جلب البيانات وتحديث السيرفر، يرجى إعادة الضغط أو اختيار إطار زمني آخر.")
else:
    data_slice = df.tail(60)
    last_row = df.iloc[-1]
    
    close_p = float(last_row['Close'])
    atr_v = float(last_row['ATR'])

    # تحديد اتجاه السوق
    ema50 = float(last_row['EMA_50']) if pd.notnull(last_row['EMA_50']) else close_p
    ema200 = float(last_row['EMA_200']) if pd.notnull(last_row['EMA_200']) else close_p
    rsi_v = float(last_row['RSI']) if pd.notnull(last_row['RSI']) else 50

    is_bullish = (ema50 >= ema200) and (rsi_v >= 50)

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

    # عرض البيانات
    st.markdown(f"### 📢 حالة السوق: **{trend_status}**")
    st.markdown(f"**السعر الحالي:** `${close_p:,.2f}` | **وقف الخسارة (SL):** `${sl_price:,.2f}` (`{sl_pct:+.2f}%`)")

    st.markdown("#### 🎯 الأهداف المتوقعة ونسبة التغير المئوية:")
    cols = st.columns(5)
    for idx, (name, val, pct) in enumerate(targets):
        cols[idx].metric(name, f"${val:,.2f}", f"{pct:+.2f}%")

    # الرسم البياني
    fig = go.Figure()

    date_col = 'Datetime' if 'Datetime' in data_slice.columns else 'Date'

    fig.add_trace(go.Candlestick(
        x=data_slice[date_col],
        open=data_slice['Open'], high=data_slice['High'],
        low=data_slice['Low'], close=data_slice['Close'],
        name="السعر"
    ))

    fig.add_trace(go.Scatter(x=data_slice[date_col], y=data_slice['EMA_50'], name="EMA 50", line=dict(color='cyan', width=1)))
    fig.add_trace(go.Scatter(x=data_slice[date_col], y=data_slice['EMA_200'], name="EMA 200", line=dict(color='orange', width=1)))

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
    
