import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="بوت تحليل الذهب والبتكوين", layout="centered")

st.title("📈 بوت التحليل الفني السريع")
st.write("تحليل لحظي للذهب والبتكوين")

symbol = st.selectbox("اختر الأصل للتحليل:", ["الذهب (XAU/USD)", "البتكوين (BTC/USD)"])
ticker = "GC=F" if symbol == "الذهب (XAU/USD)" else "BTC-USD"
frame = st.selectbox("الإطار الزمني:", ["1d", "1h", "15m"])

if st.button("تحليل الآن 🚀"):
    data = yf.download(ticker, period="1mo", interval=frame)
    
    if not data.empty:
        close_prices = data['Close'].squeeze()
        sma_20 = close_prices.rolling(window=20).mean()
        
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        last_price = float(close_prices.iloc[-1])
        last_sma = float(sma_20.iloc[-1])
        last_rsi = float(rsi.iloc[-1])
        
        st.metric(label="السعر الحالي", value=f"${last_price:,.2f}")
        
        st.subheader("نتيجة التحليل:")
        if last_price > last_sma and last_rsi < 70:
            st.success("🟢 **إشارة: شراء (Buy)** - السعر فوق المتوسط والمؤشر غير متضخم.")
        elif last_price < last_sma and last_rsi > 30:
            st.error("🔴 **إشارة: بيع (Sell)** - السعر تحت المتوسط والمؤشر سلبي.")
        else:
            st.warning("🟡 **إشارة: انتظار (Hold)** - السوق في حالة تذبذب أو عدم وضوح.")
            
        st.write(f"- مؤشر القوة النسبية (RSI): **{last_rsi:.1f}**")
        st.write(f"- متوسط 20 شمعة (SMA): **${last_sma:,.2f}**")
        
        chart_data = pd.DataFrame({'Close': close_prices, 'SMA_20': sma_20})
        st.line_chart(chart_data)
    else:
        st.error("تعذر جلب البيانات، يرجى المحاولة لاحقاً.")
      
