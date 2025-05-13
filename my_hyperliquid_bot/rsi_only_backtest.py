import pandas as pd
import matplotlib.pyplot as plt
from fetch_candles import fetch_candles
import time
import datetime

# --- データ取得 ---
symbol = "BTC"
interval = "30m"
days = 5
df = fetch_candles(symbol, interval, days)
if df is None:
    raise Exception("Failed to fetch candle data.")

# 数値型への変換
df['h'] = pd.to_numeric(df['h'], errors='coerce')
df['l'] = pd.to_numeric(df['l'], errors='coerce')
df['c'] = pd.to_numeric(df['c'], errors='coerce')

# --- RSIの計算 ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- ATRの計算 ---
def calculate_atr(df, period=14):
    df['prev_close'] = df['c'].shift(1)
    
    tr1 = df['h'] - df['l']
    tr2 = (df['h'] - df['prev_close']).abs()
    tr3 = (df['l'] - df['prev_close']).abs()
    
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = df['tr'].rolling(window=period, min_periods=period).mean()
    return atr

# RSIとATRを計算
df['rsi'] = calculate_rsi(df['c'], period=14)
df['atr'] = calculate_atr(df, period=14)

# --- シグナル生成（RSI + ATR） ---
def generate_signal_rsi_atr(row, rsi_lower=30, rsi_upper=70, atr_threshold=1.0):
    """
    row: DataFrameの各行 (Series) で、'rsi' と 'atr' が含まれている前提
    rsi_lower: RSIがこの値以下なら「売られすぎ」と判断（買いシグナル）
    rsi_upper: RSIがこの値以上なら「買われすぎ」と判断（売りシグナル）
    atr_threshold: ATRがこの値未満の場合、シグナルを無視する（ボラティリティが低い）
    """
    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        return None
    if row['atr'] < atr_threshold:
        return None
    
    # シンプルに、RSIがrsi_lower以下で買い、rsi_upper以上で売り
    if row['rsi'] <= rsi_lower:
        return "Buy Signal"
    elif row['rsi'] >= rsi_upper:
        return "Sell Signal"
    else:
        return None

# バックテストパラメータ
rsi_lower = 30
rsi_upper = 70
atr_threshold = 1.0

# --- バックテストループ ---
trades = []
position = None   # "long" or "short" or None
entry_price = None

# RSI, ATR共に計算に最低14本必要なので14行目以降からスタート
for idx in range(14, len(df)):
    curr = df.iloc[idx]

        
    signal = generate_signal_rsi_atr(
        curr,
        rsi_lower=rsi_lower,
        rsi_upper=rsi_upper,
        atr_threshold=atr_threshold
    )
    
    if signal is None:
        continue
    
    if signal == "Sell Signal":
        if position == "long":
            # ロングをクローズ
            exit_price = curr['c']
            profit = exit_price - entry_price
            trades.append({
                "action": "exit_long",
                "price": exit_price,
                "time": curr['datetime'],
                "profit": profit
            })
            # ショートに転換
            position = "short"
            entry_price = exit_price
            trades.append({
                "action": "enter_short",
                "price": entry_price,
                "time": curr['datetime']
            })
        elif position is None:
            position = "short"
            entry_price = curr['c']
            trades.append({
                "action": "enter_short",
                "price": entry_price,
                "time": curr['datetime']
            })
    
    elif signal == "Buy Signal":
        if position == "short":
            # ショートをクローズ
            exit_price = curr['c']
            profit = entry_price - exit_price
            trades.append({
                "action": "exit_short",
                "price": exit_price,
                "time": curr['datetime'],
                "profit": profit
            })
            # ロングに転換
            position = "long"
            entry_price = exit_price
            trades.append({
                "action": "enter_long",
                "price": entry_price,
                "time": curr['datetime']
            })
        elif position is None:
            position = "long"
            entry_price = curr['c']
            trades.append({
                "action": "enter_long",
                "price": entry_price,
                "time": curr['datetime']
            })

# 最終行でポジションをクローズ（任意）
if position is not None:
    final_price = df.iloc[-1]['c']
    if position == "long":
        profit = final_price - entry_price
        trades.append({
            "action": "exit_long",
            "price": final_price,
            "time": df.iloc[-1]['datetime'],
            "profit": profit
        })
    elif position == "short":
        profit = entry_price - final_price
        trades.append({
            "action": "exit_short",
            "price": final_price,
            "time": df.iloc[-1]['datetime'],
            "profit": profit
        })
    position = None

# --- 結果の表示 ---
trades_df = pd.DataFrame(trades)
print(trades_df)
total_profit = trades_df[trades_df["action"].str.contains("exit")]["profit"].sum()
print("Total Profit:", total_profit)

# trades_df: 各トレードの 'profit' が記録されている DataFrame
# 'profit' は正なら勝ち、負なら負け

total_trades = len(trades_df)
winning_trades = trades_df[trades_df['profit'] > 0]
losing_trades = trades_df[trades_df['profit'] < 0]

win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
loss_rate = len(losing_trades) / total_trades if total_trades > 0 else 0

# 平均勝ちと平均負け（金額の絶対値で）
average_win = winning_trades['profit'].mean() if not winning_trades.empty else 0
average_loss = abs(losing_trades['profit'].mean()) if not losing_trades.empty else 0

expected_value = (win_rate * average_win) - (loss_rate * average_loss)

print("Total Trades:", total_trades)
print("Win Rate:", win_rate)
print("Average Win:", average_win)
print("Average Loss:", average_loss)
print("Expected Value per Trade:", expected_value)


# --- グラフ表示 ---
plt.figure(figsize=(12,6))
plt.plot(df['datetime'], df['c'], label='Close Price')
for _, trade in trades_df.iterrows():
    if "enter" in trade["action"]:
        plt.scatter(trade["time"], trade["price"], color='green', marker='^', label=trade["action"])
    elif "exit" in trade["action"]:
        plt.scatter(trade["time"], trade["price"], color='red', marker='v', label=trade["action"])
plt.xlabel("Time")
plt.ylabel("Price")
plt.title("RSI + ATR Backtest")
plt.show()
