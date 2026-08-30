import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="بوت التحليل الفني المتقدم | FVG & MACD",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stMetric {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    .signal-card {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
        font-size: 24px;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .buy-card { background-color: #064e3b; color: #34d399; border: 1px solid #059669; }
    .sell-card { background-color: #7f1d1d; color: #f87171; border: 1px solid #dc2626; }
    .neutral-card { background-color: #334155; color: #cbd5e1; border: 1px solid #475569; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. العنوان والقائمة الجانبية
# -----------------------------------------------------------------------------
st.title("📈 بوت التحليل الفني والأهداف المتقدم")
st.caption("تحليل فني لحظي معزز بمؤشرات FVG, MACD, RSI, EMA, ATR وتأكيد الأحجام")

sidebar = st.sidebar
sidebar.header("⚙️ إعدادات التحليل")

asset_options = {
    "الذهب الفوري (XAU/USD)": "GC=F", # الأكثر استقراراً وجلباً للبيانات اللحظية
    "البتكوين (BTC/USD)": "BTC-USD",
    "الإيثيريوم (ETH/USD)": "ETH-USD",
    "الفضة (XAG/USD)": "SI=F",
    "اليورو/دولار (EUR/USD)": "EURUSD=X",
    "مؤشر ناسداك (NQ=F)": "NQ=F"
}

timeframe_options = {
    "15 دقيقة (15m)": "15m",
    "ساعة واحدة (1h)": "1h",
    "4 ساعات (4h)": "1d"
}

selected_asset_label = sidebar.selectbox("اختر الأصل للتحليل:", list(asset_options.keys()))
selected_tf_label = sidebar.selectbox("الإطار الزمني:", list(timeframe_options.keys()))

symbol = asset_options[selected_asset_label]
tf = timeframe_options[selected_tf_label]

risk_multiplier = sidebar.slider("مضاعف مخاطرة ATR (لتحديد SL/TP):", 1.0, 3.0, 1.5, 0.1)

# -----------------------------------------------------------------------------
# 3. جلب البيانات المرنة مع معالجة قيود Yahoo Finance
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_market_data(ticker, interval):
    try:
        # تحديد المدة المناسبة بناءً على الفريم لمنع استجابة فارغة
        period = "5d" if interval in ["5m", "15m"] else "1mo"
        df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        
        if df.empty:
            # محاولة احتياطية مع السعر الفوري المباشر
            alt_ticker = "XAUUSD=X" if ticker == "GC=F" else ticker
            df = yf.download(tickers=alt_ticker, period="2d", interval=interval, progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# 4. دالات حساب المؤشرات الفنية
# -----------------------------------------------------------------------------
def calculate_indicators(df):
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    df['Vol_SMA'] = df['Volume'].rolling(20).mean() if 'Volume' in df.columns else 0
    
    df['Bullish_FVG'] = False
    df['Bearish_FVG'] = False
    for i in range(2, len(df)):
        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
            df.iloc[i, df.columns.get_loc('Bullish_FVG')] = True
        elif df['High'].iloc[i] < df['Low'].iloc[i-2]:
            df.iloc[i, df.columns.get_loc('Bearish_FVG')] = True
            
    return df

# -----------------------------------------------------------------------------
# 5. محرك التحليل واتخاذ القرار
# -----------------------------------------------------------------------------
def analyze_market_advanced(df, risk_mult):
    df = calculate_indicators(df)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    price = last['Close']
    atr = last['ATR'] if pd.notna(last['ATR']) else (price * 0.01)
    
    bullish_score = 0
    bearish_score = 0
    reasons = []
    
    if last['EMA20'] > last['EMA50']:
        bullish_score += 25
        reasons.append("اتجاه صاعد (EMA20 أعلى من EMA50)")
    else:
        bearish_score += 25
        reasons.append("اتجاه هابط (EMA20 أدنى من EMA50)")
        
    if last['MACD'] > last['MACD_Signal'] and last['MACD_Hist'] > prev['MACD_Hist']:
        bullish_score += 25
        reasons.append("زخم MACD إيجابي وتزايد في عمود الهيستوجرام")
    elif last['MACD'] < last['MACD_Signal'] and last['MACD_Hist'] < prev['MACD_Hist']:
        bearish_score += 25
        reasons.append("زخم MACD سلبي وتناقص في عمود الهيستوجرام")
        
    if 40 <= last['RSI'] <= 65:
        bullish_score += 20
        reasons.append("مؤشر RSI في نطاق شراء إيجابي ومتوازن")
    elif 35 <= last['RSI'] <= 60:
        bearish_score += 20
        reasons.append("مؤشر RSI في نطاق بيع سلبية متوازن")
        
    recent_bull_fvg = df['Bullish_FVG'].tail(5).any()
    recent_bear_fvg = df['Bearish_FVG'].tail(5).any()
    
    if recent_bull_fvg:
        bullish_score += 15
        reasons.append("تكون فجوة سعرية شرائية (Bullish FVG) مؤخراً")
    if recent_bear_fvg:
        bearish_score += 15
        reasons.append("تكون فجوة سعرية بيعية (Bearish FVG) مؤخراً")

    if bullish_score >= 50 and bullish_score > bearish_score:
        signal = "BUY"
        confidence = bullish_score
        sl = price - (atr * risk_mult)
        tp1 = price + (atr * risk_mult)
        tp2 = price + (atr * risk_mult * 2.0)
        tp3 = price + (atr * risk_mult * 3.0)
    elif bearish_score >= 50 and bearish_score > bullish_score:
        signal = "SELL"
        confidence = bearish_score
        sl = price + (atr * risk_mult)
        tp1 = price - (atr * risk_mult)
        tp2 = price - (atr * risk_mult * 2.0)
        tp3 = price - (atr * risk_mult * 3.0)
    else:
        signal = "NEUTRAL"
        confidence = max(bullish_score, bearish_score)
        sl, tp1, tp2, tp3 = None, None, None, None

    return signal, confidence, price, sl, tp1, tp2, tp3, reasons, df

# -----------------------------------------------------------------------------
# 6. الواجهة والعرض
# -----------------------------------------------------------------------------
if st.button("🚀 تحليل وحساب الأهداف المتقدمة"):
    with st.spinner("جاري جلب البيانات وإجراء التحليل الفني الشامل..."):
        df = load_market_data(symbol, tf)
        
        if df.empty or len(df) < 15:
            st.error("تعذر جلب البيانات في الوقت الحالي. جرب تغيير الإطار الزمني إلى (15m أو 1h) أوجرب مرة أخرى.")
        else:
            signal, confidence, price, sl, tp1, tp2, tp3, reasons, df_analyzed = analyze_market_advanced(df, risk_multiplier)
            last = df_analyzed.iloc[-1]
            
            st.markdown("---")
            
            if signal == "BUY":
                st.markdown(f'<div class="signal-card buy-card">🟢 التوصية: شراء (BUY) - نسبة التأكيد: {confidence}%</div>', unsafe_allow_html=True)
            elif signal == "SELL":
                st.markdown(f'<div class="signal-card sell-card">🔴 التوصية: بيع (SELL) - نسبة التأكيد: {confidence}%</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="signal-card neutral-card">🟡 التوصية: محايد (NEUTRAL) - انتظار اكتمال التأكيدات</div>', unsafe_allow_html=True)
                
            st.subheader(f"سعر الدخول الحالي (Entry): ${price:,.2f}")
            
            if signal != "NEUTRAL":
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("🎯 الهدف الأول (TP1)", f"${tp1:,.2f}")
                col2.metric("🚀 الهدف الثاني (TP2)", f"${tp2:,.2f}")
                col3.metric("🔥 الهدف الثالث (TP3)", f"${tp3:,.2f}")
                col4.metric("🛑 وقف الخسارة (SL)", f"${sl:,.2f}")
            
            st.markdown("---")
            
            st.write("### 📊 ملخص المؤشرات والتأكيدات")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("RSI (14)", f"{last['RSI']:.2f}" if pd.notna(last['RSI']) else "N/A")
            col_b.metric("MACD Hist", f"{last['MACD_Hist']:.4f}" if pd.notna(last['MACD_Hist']) else "N/A")
            col_c.metric("ATR (التقلب)", f"${last['ATR']:,.2f}" if pd.notna(last['ATR']) else "N/A")
            col_d.metric("EMA 20 / 50", f"{last['EMA20']:.1f} / {last['EMA50']:.1f}")

            with st.expander("🔍 أسباب التوصية وشروط التوافق (Confluence Checklist)"):
                for reason in reasons:
                    st.write(f"- {reason}")
            
            st.write("### 📉 الرسم البياني والتوصية")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_analyzed.index,
                open=df_analyzed['Open'],
                high=df_analyzed['High'],
                low=df_analyzed['Low'],
                close=df_analyzed['Close'],
                name="السعر"
            ))
            fig.add_trace(go.Scatter(x=df_analyzed.index, y=df_analyzed['EMA20'], mode='lines', name='EMA 20', line=dict(color='cyan', width=1.5)))
            fig.add_trace(go.Scatter(x=df_analyzed.index, y=df_analyzed['EMA50'], mode='lines', name='EMA 50', line=dict(color='orange', width=1.5)))
            
            if signal != "NEUTRAL":
                fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="SL")
                fig.add_hline(y=tp1, line_dash="dash", line_color="green", annotation_text="TP1")
                fig.add_hline(y=tp2, line_dash="dash", line_color="lime", annotation_text="TP2")
                
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
