import streamlit as st
import backtrader as bt
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="Luxy UT God Mode - Streamlit App", layout="wide")

st.title("📊 Luxy UT God Mode Trading Bot")

# ------------------------------------------------------------------
# STRATEGY CLASS
# ------------------------------------------------------------------
class LuxyUTGodMode(bt.Strategy):
    params = (
        ('sensitivity', 1.2),
        ('atr_period', 7),
        ('enable_whipsaw', False),
        ('adx_len', 14),
        ('adx_thresh', 15.0),
        ('rsi_filter', False),
        ('rsi_len', 14),
        ('rsi_ob', 70.0),
        ('rsi_os', 30.0),
        ('risk_pct', 0.01),
        ('atr_len_sl', 14),
        ('atr_mult_sl', 1.5),
        ('tp1_mult', 1.0),
        ('tp2_mult', 2.0),
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.atr_sl = bt.indicators.ATR(period=self.p.atr_len_sl)
        self.adx = bt.indicators.ADX(period=self.p.adx_len)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_len)
        
        self.ut_line = 0.0
        self.position_dir = 0

    def next(self):
        n_loss = self.p.sensitivity * self.atr[0]
        src = self.data.close[0]
        prev_src = self.data.close[-1]
        prev_stop = self.ut_line if self.ut_line != 0.0 else src

        if src > prev_stop and prev_src > prev_stop:
            current_stop = max(prev_stop, src - n_loss)
        elif src < prev_stop and prev_src < prev_stop:
            current_stop = min(prev_stop, src + n_loss)
        elif src > prev_stop:
            current_stop = src - n_loss
        else:
            current_stop = src + n_loss

        self.ut_line = current_stop

        prev_dir = self.position_dir
        if prev_src <= prev_stop and src > current_stop:
            self.position_dir = 1
        elif prev_src >= prev_stop and src < current_stop:
            self.position_dir = -1

        adx_pass = not self.p.enable_whipsaw or (self.adx[0] > self.p.adx_thresh)
        rsi_pass = not self.p.rsi_filter or (self.p.rsi_os < self.rsi[0] < self.rsi_ob)

        buy_signal = (self.position_dir == 1 and prev_dir != 1) and adx_pass and rsi_pass
        sell_signal = (self.position_dir == -1 and prev_dir != -1) and adx_pass and rsi_pass

        if not self.position:
            if buy_signal:
                sl_price = src - (self.atr_sl[0] * self.p.atr_mult_sl)
                risk_amount = self.broker.getvalue() * self.p.risk_pct
                risk_per_unit = src - sl_price
                
                if risk_per_unit > 0:
                    size = risk_amount / risk_per_unit
                    self.buy(size=size)

            elif sell_signal:
                sl_price = src + (self.atr_sl[0] * self.p.atr_mult_sl)
                risk_amount = self.broker.getvalue() * self.p.risk_pct
                risk_per_unit = sl_price - src
                
                if risk_per_unit > 0:
                    size = risk_amount / risk_per_unit
                    self.sell(size=size)

# ------------------------------------------------------------------
# STREAMLIT UI & RUNNER
# ------------------------------------------------------------------
st.sidebar.header("إعدادات الاستراتيجية")
ticker = st.sidebar.text_input("رمز الأداة المالية", "GC=F")
sensitivity = st.sidebar.number_input("Sensitivity", value=1.2, step=0.1)
atr_period = st.sidebar.number_input("ATR Period", value=7, step=1)
risk_pct = st.sidebar.number_input("Risk % per trade", value=1.0, step=0.1) / 100.0

if st.button("تشغيل الاختبار (Run Backtest)"):
    st.write("جاري تحميل البيانات والاختبار...")
    
    # 1. Fetch data
    df = yf.download(ticker, start="2025-01-01")
    
    # 2. FIX MULTIINDEX COLUMNS FOR BACKTRADER (Solves AttributeError)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [str(col).capitalize() for col in df.columns]
    df.dropna(inplace=True)
    
    # 3. Setup Cerebro Engine
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    cerebro.addstrategy(
        LuxyUTGodMode,
        sensitivity=sensitivity,
        atr_period=int(atr_period),
        risk_pct=risk_pct
    )
    
    start_cash = 10000.0
    cerebro.broker.setcash(start_cash)
    
    cerebro.run()
    
    final_val = cerebro.broker.getvalue()
    st.success(f"الرصيد الأولي: ${start_cash:,.2f}")
    st.success(f"الرصيد النهائي: ${final_val:,.2f}")
    st.info(f"صافي الربح/الخسارة: ${final_val - start_cash:,.2f}")
    
