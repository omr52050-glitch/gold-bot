import yfinance as yf
import pandas as pd

# 1. تحميل البيانات
df = yf.download('GC=F', start='2025-01-01')

# 2. إصلاح الأعمدة لإزالة MultiIndex لتتوافق مع Backtrader
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# 3. التأكد من تحويل أسماء الأعمدة للأحرف الأولى الكبيرة
df.columns = [str(col).capitalize() for col in df.columns]

# 4. إزالة أي قيم مفقودة
df.dropna(inplace=True)

# 5. تمرير البيانات إلى Backtrader
data = bt.feeds.PandasData(dataname=df)
