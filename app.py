import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go

# ضبط إعدادات الصفحة للهاتف
st.set_page_config(page_title="محلل الذهب", layout="wide", initial_sidebar_state="collapsed")

st.title("🏆 محلل الذهب الذكي (XAUUSD)")

# شريط الخيارات علوي للهاتف
timeframe = st.selectbox("اختر الإطار الزمني:", ["15m", "1h", "4h", "1d"], index=1)

@st.cache_data(ttl=60)
def load_data(tf):
    period = "1mo" if tf in ["15m", "1h"] else "1y"
    df = yf.download(tickers="GC=F", period=period, interval=tf)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # حساب المؤشرات
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    return df.dropna()

df = load_data(timeframe)
data_slice = df.tail(60)

# رسم الشارت التفاعلي باستخدام Plotly (ممتاز للمس بالهاتف)
fig = go.Figure()

# إضافة الشموع اليابانية
fig.add_trace(go.Candlestick(
    x=data_slice.index,
    open=data_slice['Open'], high=data_slice['High'],
    low=data_slice['Low'], close=data_slice['Close'],
    name="السعر"
))

# إضافة المتوسطات
fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_50'], name="EMA 50", line=dict(color='cyan', width=1)))
fig.add_trace(go.Scatter(x=data_slice.index, y=data_slice['EMA_200'], name="EMA 200", line=dict(color='orange', width=1)))

# التحقق من الإشارات الأخيرة
last_row = df.iloc[-1]
prev_row = df.iloc[-2]

buy_cond = (last_row['EMA_50'] > last_row['EMA_200']) and (prev_row['MACD'] < prev_row['MACD_Signal'] and last_row['MACD'] > last_row['MACD_Signal']) and (last_row['RSI'] > 50)
sell_cond = (last_row['EMA_50'] < last_row['EMA_200']) and (prev_row['MACD'] > prev_row['MACD_Signal'] and last_row['MACD'] < last_row['MACD_Signal']) and (last_row['RSI'] < 50)

close_p = float(last_row['Close'])
atr_v = float(last_row['ATR'])

if buy_cond:
    sl, tp = close_p - (atr_v * 1.5), close_p + ((close_p - (close_p - atr_v * 1.5)) * 2.0)
    st.success(f"🎯 **إشارة شراء مفعلة** | الهدف (TP): {tp:.2f} | الوقف (SL): {sl:.2f}")
elif sell_cond:
    sl, tp = close_p + (atr_v * 1.5), close_p - (((close_p + atr_v * 1.5) - close_p) * 2.0)
    st.error(f"🎯 **إشارة بيع مفعلة** | الهدف (TP): {tp:.2f} | الوقف (SL): {sl:.2f}")
else:
    st.info(f"السعر الحالي: **{close_p:.2f}** | لا توجد إشارات دخول جديدة حالياً.")

fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)
