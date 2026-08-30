import backtrader as bt
import yfinance as yf
import math

class LuxyUTGodMode(bt.Strategy):
    params = (
        # UT Bot Settings
        ('sensitivity', 1.2),
        ('atr_period', 7),
        # Anti-Whipsaw (ADX)
        ('enable_whipsaw', False),
        ('adx_len', 14),
        ('adx_thresh', 15.0),
        # Signal Filters (RSI & Hull)
        ('rsi_filter', False),
        ('rsi_len', 14),
        ('rsi_ob', 70.0),
        ('rsi_os', 30.0),
        # Risk Calculator & SL/TP
        ('risk_pct', 0.01),      # 1% risk per trade
        ('atr_len_sl', 14),
        ('atr_mult_sl', 1.5),
        ('tp1_mult', 1.0),
        ('tp2_mult', 2.0),
    )

    def __init__(self):
        # Indicators Initialization
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.atr_sl = bt.indicators.ATR(period=self.p.atr_len_sl)
        self.adx = bt.indicators.ADX(period=self.p.adx_len)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_len)
        
        # UT Bot Buffers
        self.ut_line = 0.0
        self.position_dir = 0  # 1 for Bullish, -1 for Bearish

    def next(self):
        # Calculate Trailing Stop (UT Line)
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

        # Determine Trend Direction Change
        prev_dir = self.position_dir
        if prev_src <= prev_stop and src > current_stop:
            self.position_dir = 1
        elif prev_src >= prev_stop and src < current_stop:
            self.position_dir = -1

        # Check Filter Conditions
        adx_pass = not self.p.enable_whipsaw or (self.adx[0] > self.p.adx_thresh)
        rsi_pass = not self.p.rsi_filter or (self.p.rsi_os < self.rsi[0] < self.p.rsi_ob)

        # Signal Triggers
        buy_signal = (self.position_dir == 1 and prev_dir != 1) and adx_pass and rsi_pass
        sell_signal = (self.position_dir == -1 and prev_dir != -1) and adx_pass and rsi_pass

        # Execution Logic & Risk Management
        if not self.position:
            if buy_signal:
                sl_price = src - (self.atr_sl[0] * self.p.atr_mult_sl)
                risk_amount = self.broker.getvalue() * self.p.risk_pct
                risk_per_unit = src - sl_price
                
                if risk_per_unit > 0:
                    size = risk_amount / risk_per_unit
                    self.buy(size=size)
                    # Set Take Profit Targets
                    tp1 = src + (risk_per_unit * self.p.tp1_mult)
                    self.sell(size=size/2, exectype=bt.Order.Limit, price=tp1)

            elif sell_signal:
                sl_price = src + (self.atr_sl[0] * self.p.atr_mult_sl)
                risk_amount = self.broker.getvalue() * self.p.risk_pct
                risk_per_unit = sl_price - src
                
                if risk_per_unit > 0:
                    size = risk_amount / risk_per_unit
                    self.sell(size=size)
                    # Set Take Profit Targets
                    tp1 = src - (risk_per_unit * self.p.tp1_mult)
                    self.buy(size=size/2, exectype=bt.Order.Limit, price=tp1)

# ==========================================
# RUN BACKTEST (مثال لتشغيل الاستراتيجية)
# ==========================================
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    
    # تحميل بيانات الذهب كمثال (XAUUSD)
    data = bt.feeds.PandasData(dataname=yf.download('GC=F', start='2025-01-01'))
    cerebro.adddata(data)
    
    # إضافة الاستراتيجية ورأس المال
    cerebro.addstrategy(LuxyUTGodMode)
    cerebro.broker.setcash(10000.0)
    
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    cerebro.run()
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    # رسم البيان مع المؤشرات
    cerebro.plot(style='candlestick')
    
