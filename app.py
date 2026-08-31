import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# إعدادات الصفحة
st.set_page_config(
    page_title="منصة تحليل أسعار الذهب اللحظية",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# تخصيص الـ CSS لمعالجة تداخل القائمة الجانبية ودعم الاتجاه العربي
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    /* ضبط اتجاه المحتوى الرئيسي فقط لتجنب تداخل القائمة الجانبية */
    .main .block-container {
        direction: rtl;
        text-align: right;
    }
    
    /* ضبط القائمة الجانبية بشكل مستقل */
    section[data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    
    /* تحسين إحصائيات الأهداف والمؤشرات */
    [data-testid="stMetricValue"] {
        font-size: 20px !important;
        font-weight: bold;
    }
    
    .signal-box {
        padding: 12px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 15px;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
    }
    .buy-signal { background-color: #0e3a2f; color: #26a69a; border: 1px solid #26a69a; }
    .sell-signal { background-color: #3b1c1c; color: #ef5350; border: 1px solid #ef5350; }
    .neutral-signal { background-color: #2a2e39; color: #b2b5be; border: 1px solid #434651; }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def fetch_gold_data(ticker_symbol="GC=F", period="5d", interval="15m"):
    try:
        gold = yf.Ticker(ticker_symbol)
        df = gold.history(period=period, interval=interval)
        return df if not df.empty else None
    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
        return None


def calculate_indicators(df):
    data = df.copy()

    # 1. المتوسطات المتحركة الأسية
    data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA_21"] = data["Close"].ewm(span=21, adjust=False).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    # 2. RSI
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # 3. Stochastic Oscillator
    low_14 = data["Low"].rolling(window=14).min()
    high_14 = data["High"].rolling(window=14).max()
    data["%K"] = 100 * ((data["Close"] - low_14) / (high_14 - low_14))
    data["%D"] = data["%K"].rolling(window=3).mean()

    # 4. MACD
    exp1 = data["Close"].ewm(span=12, adjust=False).mean()
    exp2 = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = exp1 - exp2
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

    # 5. ATR
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close = (data["Low"] - data["Close"].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data["ATR"] = true_range.rolling(14).mean()

    return data


def calculate_targets(df, signal_type):
    latest = df.iloc[-1]
    current_price = latest["Close"]
    atr = latest["ATR"] if not pd.isna(latest["ATR"]) else 2.5

    recent_high = df["High"].tail(15).max()
    recent_low = df["Low"].tail(15).min()

    targets = {}

    if "شراء" in signal_type:
        targets["type"] = "BUY"
        targets["tp1"] = current_price + (1.2 * atr)
        targets["tp2"] = current_price + (2.5 * atr)
        targets["sl"] = current_price - (1.2 * atr)
    elif "بيع" in signal_type:
        targets["type"] = "SELL"
        targets["tp1"] = current_price - (1.2 * atr)
        targets["tp2"] = current_price - (2.5 * atr)
        targets["sl"] = current_price + (1.2 * atr)
    else:
        targets["type"] = "NEUTRAL"
        targets["support"] = recent_low
        targets["resistance"] = recent_high

    return targets


def analyze_signals(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    reasons = []
    buy_score = 0
    sell_score = 0

    if prev["EMA_9"] <= prev["EMA_21"] and latest["EMA_9"] > latest["EMA_21"]:
        buy_score += 2
        reasons.append("تقاطع إيجابي سريح (EMA 9 يعبر أعلى EMA 21).")
    elif prev["EMA_9"] >= prev["EMA_21"] and latest["EMA_9"] < latest["EMA_21"]:
        sell_score += 2
        reasons.append("تقاطع سلبي سريع (EMA 9 يعبر أدنى EMA 21).")

    if latest["%K"] < 20 and latest["%K"] > latest["%D"]:
        buy_score += 1.5
        reasons.append(f"مؤشر الاستوكاستك يتشبع بيعياً ({latest['%K']:.1f}).")
    elif latest["%K"] > 80 and latest["%K"] < latest["%D"]:
        sell_score += 1.5
        reasons.append(f"مؤشر الاستوكاستك يتشبع شرائياً ({latest['%K']:.1f}).")

    if prev["MACD"] <= prev["MACD_Signal"] and latest["MACD"] > latest["MACD_Signal"]:
        buy_score += 1.5
        reasons.append("تقاطع إيجابي لمؤشر MACD.")
    elif prev["MACD"] >= prev["MACD_Signal"] and latest["MACD"] < latest["MACD_Signal"]:
        sell_score += 1.5
        reasons.append("تقاطع سلبي لمؤشر MACD.")

    rsi = latest["RSI"]
    if rsi < 35:
        buy_score += 1
        reasons.append(f"مؤشر RSI أدنى من 35 ({rsi:.1f}).")
    elif rsi > 65:
        sell_score += 1
        reasons.append(f"مؤشر RSI أعلى من 65 ({rsi:.1f}).")

    if buy_score >= 3.5:
        signal_text = "شراء قوي 🚀"
        signal_class = "buy-signal"
    elif buy_score > sell_score:
        signal_text = "شراء (Buy) 📈"
        signal_class = "buy-signal"
    elif sell_score >= 3.5:
        signal_text = "بيع قوي 🔻"
        signal_class = "sell-signal"
    elif sell_score > buy_score:
        signal_text = "بيع (Sell) 📉"
        signal_class = "sell-signal"
    else:
        signal_text = "محايد (Neutral) ⚖️"
        signal_class = "neutral-signal"

    return signal_text, signal_class, reasons


# --- القائمة الجانبية ---
st.sidebar.title("🪙 الإعدادات")
interval_option = st.sidebar.selectbox(
    "اختر الفريم الزمني:",
    ["15 دقيقة (15m)", "5 دقائق (5m)"],
    index=0
)

interval = "15m" if "15m" in interval_option else "5m"
period = "1d" if interval == "5m" else "5d"

# --- الواجهة الرئيسية ---
st.title(f"📊 تحليل الذهب - فريم ({interval})")

df_raw = fetch_gold_data("GC=F", period=period, interval=interval)

if df_raw is not None and not df_raw.empty:
    df = calculate_indicators(df_raw)
    signal_text, signal_class, reasons = analyze_signals(df)
    targets = calculate_targets(df, signal_text)

    # عرض التوصية والأهداف بدون تداخل
    st.subheader("التوصية الحالية")
    st.markdown(f'<div class="signal-box {signal_class}">{signal_text}</div>', unsafe_allow_html=True)
    
    st.markdown("**أسباب الإشارة:**")
    for r in reasons:
        st.markdown(f"- {r}")

    st.markdown("---")

    st.subheader("🎯 الأهداف والوقف اللحظي")
    if targets["type"] in ["BUY", "SELL"]:
        m1, m2, m3 = st.columns(3)
        m1.metric("الهدف 1 (TP1)", f"${targets['tp1']:.2f}")
        m2.metric("الهدف 2 (TP2)", f"${targets['tp2']:.2f}")
        m3.metric("الوقف (SL)", f"${targets['sl']:.2f}", delta_color="inverse")
    else:
        m1, m2 = st.columns(2)
        m1.metric("المقاومة اللحظية", f"${targets['resistance']:.2f}")
        m2.metric("الدعم اللحظي", f"${targets['support']:.2f}")

    st.markdown("---")

    # الرسم البياني المتعدد
    st.subheader("📈 رسم الشموع والمؤشرات")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="الذهب"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], name="EMA 9", line=dict(color="#FF9800", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], name="EMA 21", line=dict(color="#2196F3", width=1.5)), row=1, col=1)

    if targets["type"] in ["BUY", "SELL"]:
        fig.add_hline(y=targets["tp1"], line_dash="dot", line_color="#26a69a", annotation_text="TP1", row=1, col=1)
        fig.add_hline(y=targets["tp2"], line_dash="dash", line_color="#26a69a", annotation_text="TP2", row=1, col=1)
        fig.add_hline(y=targets["sl"], line_dash="solid", line_color="#ef5350", annotation_text="SL", row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['%K'], name="%K", line=dict(color="#00E676", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['%D'], name="%D", line=dict(color="#FF1744", width=1.5)), row=2, col=1)
    fig.add_hline(y=80, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=20, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("تعذر جلب البيانات. يرجى إعادة المحاولة.")
    
