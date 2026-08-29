import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="بوت تحليل الذهب والبتكوين", layout="centered")

st.title("📈 بوت التحليل الفني والأهداف")
st.write("تحليل لحظي مع نقاط الدخول، الأهداف، ووقف الخسارة")

symbol = st.selectbox("اختر الأصل للتحليل:", ["الذهب (XAU/USD)", "البتكوين (BTC/USD)"])
ticker = "XAUUSD=X" if symbol == "الذهب (XAU/USD)" else "BTC-USD"

frame = st.selectbox("الإطار الزمني:", ["1d", "1h", "15m", "5m"])

if st.button("تحليل وحساب الأهداف 🚀"):
    # تحديد الفترة بعناية لضمان استجابة Yahoo Finance للإطارات الصغيرة
    if frame == "5m":
        fetch_period = "5d"
    elif frame == "15m":
        fetch_period = "1mo"
    else:
        fetch_period = "1mo"
    
    with st.spinner('جاري جلب البيانات...'):
        data = yf.download(ticker, period=fetch_period, interval=frame, progress=False)
    
    if not data.empty and len(data) >= 20:
        close_prices = data['Close'].squeeze()
        high_prices = data['High'].squeeze()
        low_prices = data['Low'].squeeze()
        
        # حساب SMA 20
        sma_20 = close_prices.rolling(window=20).mean()
        
        # حساب RSI 14
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # حساب ATR
        tr = np.maximum(high_prices - low_prices, 
                        np.maximum(abs(high_prices - close_prices.shift(1)), 
                                   abs(low_prices - close_prices.shift(1))))
        atr = tr.rolling(14).mean().iloc[-1]
        
        last_price = float(close_prices.iloc[-1])
        last_sma = float(sma_20.iloc[-1])
        last_rsi = float(rsi.iloc[-1])
        
        st.metric(label="سعر الدخول الحالي (Entry)", value=f"${last_price:,.2f}")
        
        if last_price > last_sma and last_rsi < 70:
            signal = "BUY"
            st.success("🟢 **التوصية: شراء (BUY)**")
            stop_loss = last_price - (1.5 * atr)
            tp1 = last_price + (1.5 * atr)
            tp2 = last_price + (3.0 * atr)
        elif last_price < last_sma and last_rsi > 30:
            signal = "SELL"
            st.error("🔴 **التوصية: بيع (SELL)**")
            stop_loss = last_price + (1.5 * atr)
            tp1 = last_price - (1.5 * atr)
            tp2 = last_price - (3.0 * atr)
        else:
            signal = "WAIT"
            st.warning("🟡 **التوصية: انتظار (HOLD) - لا تدخل الآن**")
            stop_loss = tp1 = tp2 = 0

        if signal != "WAIT":
            st.markdown("---")
            st.subheader("🎯 تفاصيل الصفقة:")
            col1, col2, col3 = st.columns(3)
            col1.metric("🛑 وقف الخسارة (SL)", f"${stop_loss:,.2f}")
            col2.metric("🎯 الهدف الأول (TP1)", f"${tp1:,.2f}")
            col3.metric("🚀 الهدف الثاني (TP2)", f"${tp2:,.2f}")
            
            st.write(f"- مؤشر RSI: **{last_rsi:.1f}**")
            st.write(f"- نطاق التقلب (ATR): **${atr:,.2f}**")
        
        chart_data = pd.DataFrame({'Close': close_prices, 'SMA_20': sma_20})
        st.line_chart(chart_data)
    else:
        st.error("تعذر جلب البيانات لهذا الإطار حالياً (قد يكون السوق مغلقاً أو التايم فريم غير متاح). جرب إطار 15m أو 1h.")
        
