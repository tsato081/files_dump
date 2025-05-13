import pandas as pd
import matplotlib.pyplot as plt
from fetch_candles import fetch_candles
import time
import datetime


# RSI x MA Strategy

def calculate_rsi(series, period=14):
    """
    終値のSeriesからRSIを計算する関数
    Args:
        series (pd.Series): 終値の時系列データ
        period (int): RSIの計算期間（デフォルト14）
    Returns:
        pd.Series: RSI値
    """
    delta = series.diff()
    # 利上げと下げを分ける
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 平均上昇・平均下降を計算（単純移動平均の場合）
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # 初期値の計算後、RSIは後続の値に対してEMA的に更新する方法もあるが、ここではシンプルにSMAを使います
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# --- データ取得 ---
symbol = "BTC"
interval = "15m"
days = 100
df = fetch_candles(symbol, interval, days)
if df is None:
    raise Exception("Failed to fetch candle data.")

# --- 移動平均計算 ---
short_window = 5
long_window = 20
df['c'] = pd.to_numeric(df['c'])
df['ma_short'] = df['c'].rolling(window=short_window).mean()
df['ma_long'] = df['c'].rolling(window=long_window).mean()

print(df)

# 'c' 列は終値なので、そのSeriesからRSIを計算する
df['rsi'] = calculate_rsi(df['c'], period=14)

# 確認用に先頭数行を表示
print(df[['datetime', 'c', 'rsi']].head(20))


# --- シグナル生成ロジック---
def generate_signal(prev, curr, rsi_threshold_buy=50, rsi_threshold_sell=50):
    # MAが計算されているかチェック
    if pd.isna(prev['ma_short']) or pd.isna(prev['ma_long']) or pd.isna(curr['ma_short']) or pd.isna(curr['ma_long']):
        return None
    
    # RSIも両期間でチェック（ここでは最新のRSIを使う例）
    if pd.isna(curr['rsi']):
        return None
    
    # MAクロスのシグナル
    if prev['ma_short'] < prev['ma_long'] and curr['ma_short'] > curr['ma_long']:
        # 買いシグナルなら、RSIが閾値以上の場合のみ有効
        if curr['rsi'] >= rsi_threshold_buy:
            return "Buy Signal"
    elif prev['ma_short'] > prev['ma_long'] and curr['ma_short'] < curr['ma_long']:
        # 売りシグナルなら、RSIが閾値以下の場合のみ有効
        if curr['rsi'] <= rsi_threshold_sell:
            return "Sell Signal"
    return None


    
# --- バックテストループ ---
trades = []
position = None   # 現在のポジション: None, "long", "short"
entry_price = None

for idx in range(1, len(df)):
    prev = df.iloc[idx - 1]
    curr = df.iloc[idx]
    
    signal = generate_signal(prev, curr)
    
    if signal is None:
        continue
    
    if signal == "Sell Signal":
        if position == 'long':
            exit_price = curr['c']
            profit = exit_price - entry_price
            trades.append({"action": "exit_long", "price": exit_price, "time": curr['datetime'], "profit": profit})
            
            position = 'short'
            entry_price = exit_price
            trades.append({"action": "enter_short", "price": entry_price, "time": curr['datetime']})
            
        elif position is None:
            position = 'short'
            entry_price = curr['c']
            trades.append({"action": "enter_short", "price": entry_price, "time": curr['datetime']})
    
    elif signal == 'Buy Signal':
        
        if position == "short":
            
            exit_price = curr['c']
            profit = entry_price - exit_price
            trades.append({"action": "exit_short", "price": exit_price, "time": curr['datetime'], "profit": profit})
            
            # 同時にロングポジションを開始
            position = "long"
            entry_price = exit_price
            trades.append({"action": "enter_long", "price": entry_price, "time": curr['datetime']})
            
        elif position is None:
            
            position = "long"
            entry_price = curr['c']
            trades.append({"action": "enter_long", "price": entry_price, "time": curr['datetime']})
            
if position is not None:
    final_price = df.iloc[-1]['c']
    
    if position == "long":
        profit = final_price - entry_price
        trades.append({"action": "exit_long", "price": final_price, "time": df.iloc[-1]['datetime'], "profit": profit})
        
    elif position == "short":
        profit = entry_price - final_price
        trades.append({"action": "exit_short", "price": final_price, "time": df.iloc[-1]['datetime'], "profit": profit})
    position = None


# --- 結果の表示 ---
trades_df = pd.DataFrame(trades)
print(trades_df)
total_profit = trades_df[trades_df["action"].str.contains("exit")]["profit"].sum()
print("Total Profit:", total_profit)


# --- グラフ表示 ---
plt.figure(figsize=(12,6))
plt.plot(df['datetime'], df['c'], label='Close Price')
for _, trade in trades_df.iterrows():
    if "enter" in trade["action"]:
        plt.scatter(trade["time"], trade["price"], color='yellow', marker='v', label=trade["action"])
    elif "exit" in trade["action"]:
        plt.scatter(trade["time"], trade["price"], color='red', marker='o', label=trade["action"])
plt.xlabel("Time")
plt.ylabel("Price")
plt.title("Backtest: Trade Entries and Exits")
plt.show()



            