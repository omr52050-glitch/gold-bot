import datetime
import pandas as pd
import yfinance as yf


def fetch_gold_data(period="6mo", interval="1d"):
    """جلب بيانات أسعار الذهب (GC=F) من Yahoo Finance"""
    gold = yf.Ticker("GC=F")
    df = gold.history(period=period, interval=interval)
    return df


def calculate_indicators(df):
    """حساب المؤشرات الفنية: المتوسطات المتحركة ومؤشر RSI"""
    # حساب المتوسطات المتحركة لمدة 20 و 50 يوماً
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["SMA_50"] = df["Close"].rolling(window=50).mean()

    # حساب مؤشر القوة النسبية (RSI) لمدة 14 يوماً
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def generate_signals(df):
    """توليد الإشارات بناءً على التحليل الفني"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price = latest["Close"]
    rsi = latest["RSI"]
    sma_20 = latest["SMA_20"]
    sma_50 = latest["SMA_50"]

    signal = "محايد (Neutral)"
    reasons = []

    # إشارات التقاطع (Golden / Death Cross)
    if prev["SMA_20"] < prev["SMA_50"] and sma_20 > sma_50:
        signal = "شراء قوي (Strong Buy)"
        reasons.append("تقاطع إيجابي للمتوسطات المتحركة (Golden Cross)")
    elif prev["SMA_20"] > prev["SMA_50"] and sma_20 < sma_50:
        signal = "بيع قوي (Strong Sell)"
        reasons.append("تقاطع سلبي للمتوسطات المتحركة (Death Cross)")

    # تقييم RSI
    if rsi < 30:
        reasons.append("مؤشر RSI يدل على تشبع بيعي (فرصة شراء)")
        if signal == "محايد (Neutral)":
            signal = "شراء (Buy)"
    elif rsi > 70:
        reasons.append("مؤشر RSI يدل على تشبع شرائي (فرصة بيع)")
        if signal == "محايد (Neutral)":
            signal = "بيع (Sell)"

    return {
        "Price": price,
        "RSI": rsi,
        "SMA_20": sma_20,
        "SMA_50": sma_50,
        "Signal": signal,
        "Reasons": reasons,
    }


# --- تشغيل التحليل ---
if __name__ == "__main__":
    print("جاري جلب بيانات الذهب وتحليلها...\n")
    data = fetch_gold_data()
    analyzed_data = calculate_indicators(data)
    result = generate_signals(analyzed_data)

    print(f"=== تقرير تحليل الذهب ({datetime.date.today()}) ===")
    print(f"السعر الحالي: ${result['Price']:.2f}")
    print(f"مؤشر RSI: {result['RSI']:.2f}")
    print(f"المتوسط المتحرك 20: ${result['SMA_20']:.2f}")
    print(f"المتوسط المتحرك 50: ${result['SMA_50']:.2f}")
    print(f"\nالتوصية: {result['Signal']}")
    if result["Reasons"]:
        print("الأسباب:")
        for r in result["Reasons"]:
            print(f"- {r}")
            
