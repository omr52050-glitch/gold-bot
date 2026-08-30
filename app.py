import streamlit as st
import pandas as pd
import requests
import ta
import plotly.graph_objects as go
import yfinance as yf

# إعدادات الصفحة
st.set_page_config(page_title="منصة التحليل الرقمي الذكي", layout="wide", initial_sidebar_state="collapsed")

st.title("⚡ منصة التحليل الفني المباشر (تحديث لحظي)")

# القوائم العلوية
col_symbol, col_tf, col_btn = st.columns([2, 2, 1])

with col_symbol:
    asset = st.selectbox("اختر زوج التداول:", ["البتكوين (BTCUSDT)", "الذهب (XAUUSD)"])

with col_tf:
    timeframe = st.selectbox("الإطار الزمني:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)

with col_btn:
    st.write("")
    st.write("")
    if st.button("🔄 تحديث السعر"):
        st.rerun()

# جلب بيانات البتكوين مباشرة عبر API بـ User-Agent موثوق
def fetch_binance_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    res = requests.get(url, headers=headers, timeout=10)
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

# جلب بيانات الذهب عبر yfinance مع تحديد الفترة بمرونة
def fetch_gold_data(interval):
    period_map = {"1m": "1d", "5m": "5d", "15m": "1mo", "1h": "1mo", "4h": "2mo", "1d": "1y"}
    p = period_map.get(interval, "5d")
    
    ticker = yf.Ticker("GC=F")
    df = ticker.history(period=p, interval=interval)
    if df.empty:
        return None
    df = df.reset_index()
    return df

# جلب البيانات الحية
df = None
if asset == "البتكوين (BTCUSDT)":
    tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    try:
        df = fetch_binance_data("BTCUSDT", tf_map[timeframe])
    except Exception as e:
        st.error(f"⚠️ تعذر الاتصال بمصدر بيانات البتكوين: {e}")
else:
    try:
        df = fetch_gold_data(timeframe)
    except Exception as e:
        st.error(f"⚠️ تعذر الاتصال بمصدر بيانات الذهب: {e}")

if df is not None and not df.empty:
    close_s = df['Close']
    high_s = df['High']
    low_s = df['Low']

    # حساب المؤشرات الفنية
    df['EMA_50'] = ta.trend.ema_indicator(close_s, window=min(50, len(df)))
    df['EMA_200'] = ta.trend.ema_indicator(close_s, window=min(200, len(df)))
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

    # عرض البيانات الحية
    st.markdown(f"### 📢 حالة السوق: **{trend_status}**")
    st.markdown(f"**السعر المباشر الآن:** `${close_p:,.2f}` | **وقف الخسارة (SL):** `${sl_price:,.2f}` (`{sl_pct:+.2f}%`)")

    st.markdown("#### 🎯 الأهداف المتوقعة ونسبة التغير المئوية:")
    cols = st.columns(5)
    for idx, (name, val, pct) in enumerate(targets):
        cols[idx].metric(name, f"${val:,.2f}", f"{pct:+.2f}%")

    # رسم الشارت
    data_slice = df.tail(60)
    date_col = 'Datetime' if 'Datetime' in data_slice.columns else ('Date' if 'Date' in data_slice.columns else data_slice.columns[0])

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
else:
    st.warning("⚠️ جاري جلب الشمعات الحية، اضغط على زر 'تحديث السعر' أعلاه.")
    
