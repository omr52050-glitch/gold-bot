import streamlit as st
import pandas as pd
import requests
import ta
import plotly.graph_objects as go

# إعدادات الصفحة
st.set_page_config(page_title="منصة التحليل الرقمي الذكي", layout="wide", initial_sidebar_state="collapsed")

st.title("⚡ منصة التحليل الفني المباشر (تحديث لحظي)")

# القوائم العلوية
col_symbol, col_tf, col_btn = st.columns([2, 2, 1])

with col_symbol:
    asset = st.selectbox("اختر زوج التداول:", ["البتكوين (BTCUSDT)", "الذهب (XAUUSD)"])

with col_tf:
    timeframe = st.selectbox("الإطار الزمني:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=0)

with col_btn:
    st.write("") # محاذاة الزر
    st.write("")
    if st.button("🔄 تحديث السعر"):
        st.cache_data.clear()

# دالة جلب البيانات المباشرة بدون كاش معطل
def fetch_binance_klines(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    res = requests.get(url, timeout=5)
    data = res.json()
    
    df = pd.DataFrame(data, columns=[
        'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close_time', 'Quote_asset_volume', 'Number_of_trades',
        'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
    ])
    
    df['Datetime'] = pd.to_datetime(df['Open_time'], unit='ms')
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
        
    return df

def fetch_gold_data(interval):
    # جلب بيانات الذهب من مصدر ياهو بدون كاش طويل
    import yfinance as yf
    df = yf.Ticker("GC=F").history(period="2d", interval=interval)
    df = df.reset_index()
    return df

# جلب البيانات بناءً على الاختيار
try:
    if asset == "البتكوين (BTCUSDT)":
        tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        df = fetch_binance_klines("BTCUSDT", tf_map[timeframe])
    else:
        df = fetch_gold_data(timeframe)

    # حساب المؤشرات الفنية
    close_s = df['Close']
    high_s = df['High']
    low_s = df['Low']

    df['EMA_50'] = ta.trend.ema_indicator(close_s, window=min(50, len(df)-1))
    df['EMA_200'] = ta.trend.ema_indicator(close_s, window=min(200, len(df)-1))
    df['RSI'] = ta.momentum.rsi(close_s, window=14)
    df['ATR'] = ta.volatility.average_true_range(high_s, low_s, close_s, window=14)
    
    df = df.dropna()
    
    last_row = df.iloc[-1]
    close_p = float(last_row['Close'])
    atr_v = float(last_row['ATR'])
    
    ema50 = float(last_row['EMA_50'])
    ema200 = float(last_row['EMA_200'])
    rsi_v = float(last_row['RSI'])

    is_bullish = (ema50 >= ema200) and (rsi_v >= 50)

    # حساب الأهداف والستوب
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

    # عرض البيانات الحية
    st.markdown(f"### 📢 حالة السوق: **{trend_status}**")
    st.markdown(f"**السعر المباشر الآن:** `${close_p:,.2f}` | **وقف الخسارة (SL):** `${sl_price:,.2f}` (`{sl_pct:+.2f}%`)")

    st.markdown("#### 🎯 الأهداف المتوقعة ونسبة التغير المئوية:")
    cols = st.columns(5)
    for idx, (name, val, pct) in enumerate(targets):
        cols[idx].metric(name, f"${val:,.2f}", f"{pct:+.2f}%")

    # رسم الشارت
    data_slice = df.tail(60)
    date_col = 'Datetime' if 'Datetime' in data_slice.columns else 'Date'

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data_slice[date_col],
        open=data_slice['Open'], high=data_slice['High'],
        low=data_slice['Low'], close=data_slice['Close'],
        name="السعر المباشر"
    ))

    fig.add_trace(go.Scatter(x=data_slice[date_col], y=data_slice['EMA_50'], name="EMA 50", line=dict(color='cyan', width=1)))
    fig.add_trace(go.Scatter(x=data_slice[date_col], y=data_slice['EMA_200'], name="EMA 200", line=dict(color='orange', width=1)))

    fig.add_hline(
        y=sl_price, line_dash="solid", line_color="red", line_width=2,
        annotation_text=f"الوقف: {sl_price:,.2f}", annotation_position="bottom right"
    )

    colors = ["#76ff03", "#64dd17", "#00c853", "#00e676", "#1de9b6"]
    for idx, (name, val, pct) in enumerate(targets):
        fig.add_hline(
            y=val, line_dash="dash", line_color=colors[idx], line_width=1.5,
            annotation_text=f"{name}: {val:,.2f}", annotation_position="top right"
        )

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=550,
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("⚠️ جاري الاتصال بالسيرفر وجلب أحدث الشمعات، يرجى الضغط على زر التحديث أعلاه.")
    
