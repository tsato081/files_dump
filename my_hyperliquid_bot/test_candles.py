import os
import time
import datetime
from dotenv import load_dotenv
from hyperliquid.info import Info
import pandas as pd

load_dotenv()

info_client = Info(base_url="https://api.hyperliquid.xyz", skip_ws=True)

end_time = int(time.time() * 1000)

# 過去1日分のデータを取得するため、現在時刻から24時間前
start_time = int((datetime.datetime.now() - datetime.timedelta(days=1)).timestamp() * 1000)

print("Start Time:", start_time)
print("End Time:", end_time)

symbol = "BTC"
interval = "1h"


# candles_snapshot メソッドを呼び出してローソク足データを取得
try:
    candles_data = info_client.candles_snapshot(symbol, interval, start_time, end_time)
    print("Raw Candles Data:")
    print(candles_data)
except Exception as e:
    print("ローソク足データ取得中にエラーが発生:", e)

# 取得したデータをDataFrameに変換してみる（もしデータ形式がリストや辞書で返ってくる場合）
try:
    # ここでは、各ローソク足が辞書形式で返ってくる想定です
    df = pd.DataFrame(candles_data)
    print("\nDataFrame:")
    print(df.head())
except Exception as e:
    print("DataFrame変換中にエラーが発生:", e)
    


df['c'] = pd.to_numeric(df['c'])

# 移動平均期間を設定（例: 短期=7期間、長期=25期間）
short_window = 7
long_window = 25

# 移動平均の計算
df['ma_short'] = df['c'].rolling(window=short_window).mean()
df['ma_long']  = df['c'].rolling(window=long_window).mean()

# クロス判定用のサンプル関数
def check_ma_cross(df):
    if len(df) < long_window:
        return None  # データが少なすぎる場合
    # 最新の2本のローソク足のMA値を比較
    prev_short = df.iloc[-2]['ma_short']
    prev_long  = df.iloc[-2]['ma_long']
    curr_short = df.iloc[-1]['ma_short']
    curr_long  = df.iloc[-1]['ma_long']
    
    if pd.isna(prev_short) or pd.isna(prev_long) or pd.isna(curr_short) or pd.isna(curr_long):
        return None  # 移動平均計算がまだできていない場合
    if prev_short < prev_long and curr_short > curr_long:
        return "Golden Cross (Buy Signal)"
    elif prev_short > prev_long and curr_short < curr_long:
        return "Death Cross (Sell Signal)"
    else:
        return "No Cross"

signal = check_ma_cross(df)
print("MA Cross Signal:", signal)

# DataFrameの先頭部分を表示して確認
print(df.tail(10))
    

