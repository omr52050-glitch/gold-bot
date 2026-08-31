import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# إعدادات الصفحة
st.set_page_config(
    page_title="منصة تحليل أسعار الذهب الذكية",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# تخصيص الاتجاه والتصميم بدعم اللغة العربية بدون تداخل النصوص
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    /* تطبيق الخط العربي وتنسيق الاتجاه للواجهة الرئيسية */
    html, body, [class*="st-"], .main .block-container {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    /* إصلاح القائمة الجانبية لتجنب التداخل */
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    
    /* تحسين البطاقات والإحصائيات */
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: bold;
    }
    
    .signal-box {
        padding: 15px;
        border-radius: 10px;
        margin-top: 10px;
        margin-bottom: 15px;
        text-align: center;
        font-size: 22px;
        font-weight: bold;
    }
    .buy-signal { background-color: #0e3a2f; color: #26a69a; border: 1px solid #26a69a; }
    .sell-signal { background-color: #3b1c1c; color: #ef5350; border: 1px solid #ef5350; }
    .neutral-signal { background-color: #2a2e39; color: #b2b5be; border: 1px solid #434651; }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def fetch_gold_data(ticker_symbol="GC=F", period="6mo", interval="1d"):
    try:
        gold = yf.Ticker(ticker_symbol)
        df = gold.history(period=period, interval=interval)
        return df if not df.empty else None
    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات: {e}")
        return None


def calculate_indicators(df):
    data = df.copy()

    # المتوسطات المتحركة
    data["SMA_20"] = data["Close"].rolling(window=20).mean()
    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    # مؤشر RSI
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # مؤشر MACD
    exp1 = data["Close"].ewm(span=12, adjust=False).mean()
    exp2 = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = exp1 - exp2
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

    # حساب ATR لقياس مدى تذبذب السعر لاستخدامه في الأهداف
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
    atr = latest["ATR"] if not pd.isna(latest["ATR"]) else 15.0

    recent_high = df["High"].tail(20).max()
    recent_low = df["Low"].tail(20).min()

    targets = {}

    if "شراء" in signal_type:
        targets["type"] = "BUY"
        targets["tp1"] = current_price + (1.5 * atr)
        targets["tp2"] = max(current_price + (3.0 * atr), recent_high)
        targets["sl"] = current_price - (1.5 * atr)
    elif "بيع" in signal_type:
        targets["type"] = "SELL"
        targets["tp1"] = current_price - (1.5 * atr)
        targets["tp2"] = min(current_price - (3.0 * atr), recent_low)
        targets["sl"] = current_price + (1.5 * atr)
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

    if prev["SMA_20"] <= prev["SMA_50"] and latest["SMA_20"] > latest["SMA_50"]:
        buy_score += 2
        reasons.append("تقاطع إيجابي (Golden Cross) بين المتوسط 20 والمتوسط 50.")
    elif (
        prev["SMA_20"] >= prev["SMA_50"] and latest["SMA_20"] < latest["SMA_50"]
    ):
        sell_score += 2
        reasons.append("تقاطع سلبي (Death Cross) بين المتوسط 20 والمتوسط 50.")

    if latest["Close"] > latest["SMA_200"]:
        buy_score += 1
        reasons.append("السعر يتداول أعلى من المتوسط المتحرك 200 (اتجاه صاعد عام).")
    else:
        sell_score += 1
        reasons.append("السعر يتداول أدنى من المتوسط المتحرك 200 (اتجاه هابط عام).")

    rsi = latest["RSI"]
    if rsi < 30:
        buy_score += 2
        reasons.append(
            f"مؤشر RSI أدنى من 30 ({rsi:.1f}) - تشبع بيعي (فرصة انعكاس صعودي)."
        )
    elif rsi > 70:
        sell_score += 2
        reasons.append(
            f"مؤشر RSI أعلى من 70 ({rsi:.1f}) - تشبع شرائي (تصحيح محتمل)."
        )

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
st.sidebar.title("🪙 خيارات التحليل")
symbol_option = st.sidebar.selectbox(
    "اختر أداة الذهب:", ["عقود الذهب الآجلة (GC=F)", "صندوق الذهب (GLD)"]
)
selected_ticker = "GC=F" if "GC=F" in symbol_option else "GLD"
period = st.sidebar.select_slider(
    "النطاق الزمني:", options=["1mo", "3mo", "6mo", "1y"], value="6mo"
)

# --- الواجهة الرئيسية ---
st.title("📊 منصة تحليل الذهب وتحديد الأهداف")

df_raw = fetch_gold_data(selected_ticker, period)

if df_raw is not None and not df_raw.empty:
    df = calculate_indicators(df_raw)
    signal_text, signal_class, reasons = analyze_signals(df)
    targets = calculate_targets(df, signal_text)

    # عرض التوصية
    st.subheader("التوصية الفنية")
    st.markdown(
        f'<div class="signal-box {signal_class}">{signal_text}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**أسباب التوصية:**")
    for r in reasons:
        st.markdown(f"- {r}")

    st.markdown("---")

    # عرض الأهداف بطريقة متناسبة مع الشاشات الصغيرة والكبيرة
    st.subheader("🎯 الأهداف المستهدفة ومستويات المخاطرة")

    if targets["type"] in ["BUY", "SELL"]:
        c1, c2, c3 = st.columns(3)
        c1.metric("الهدف الأول (TP1)", f"${targets['tp1']:.2f}")
        c2.metric("الهدف الثاني (TP2)", f"${targets['tp2']:.2f}")
        c3.metric(
            "وقف الخسارة (SL)",
            f"${targets['sl']:.2f}",
            delta_color="inverse",
        )
    else:
        c1, c2 = st.columns(2)
        c1.metric("مستوى المقاومة القريب", f"${targets['resistance']:.2f}")
        c2.metric("مستوى الدعم القريب", f"${targets['support']:.2f}")

    st.markdown("---")

    # الرسم البياني
    st.subheader("📈 الرسم البياني مع الأهداف")
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="الذهب",
        )
    )

    if targets["type"] in ["BUY", "SELL"]:
        fig.add_hline(
            y=targets["tp1"],
            line_dash="dot",
            line_color="#26a69a",
            annotation_text="الهدف الأول TP1",
        )
        fig.add_hline(
            y=targets["tp2"],
            line_dash="dash",
            line_color="#26a69a",
            annotation_text="الهدف الثاني TP2",
        )
        fig.add_hline(
            y=targets["sl"],
            line_dash="solid",
            line_color="#ef5350",
            annotation_text="وقف الخسارة SL",
        )

    fig.update_layout(
        template="plotly_dark", height=500, xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("تعذر جلب البيانات. يرجى إعادة المحاولة.")
