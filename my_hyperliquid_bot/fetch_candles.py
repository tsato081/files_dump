import time
import datetime
import os
import pandas as pd
from dotenv import load_dotenv
from hyperliquid.info import Info

def fetch_candles(symbol: str, interval: str, days: int = 3, base_url: str = "https://api.hyperliquid.xyz", skip_ws: bool = True):
    """
    指定した銘柄・時間間隔で、過去 `days` 日間分のローソク足データを取得し、DataFrame として返す関数。
    
    Args:
        symbol (str): 取得する銘柄（例："BTC"）
        interval (str): 時間間隔（例："5m"）
        days (int): 過去何日分のデータを取得するか
        base_url (str): APIエンドポイント
        skip_ws (bool): WebSocketを利用せずHTTPのみで取得するかどうか
        
    Returns:
        pd.DataFrame: 取得したローソク足データ
    """
    
    # 現在時刻（ミリ秒）
    end_time = int(time.time() * 1000)
    # 3日前
    start_time = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp() * 1000)
    
    print(f"Fetching candles for {symbol} ({interval}) from {start_time} to {end_time}...")
    
    info_client = Info(base_url=base_url, skip_ws=skip_ws)
    
    try:
        candles_data = info_client.candles_snapshot(symbol, interval, start_time, end_time)
        print("Candles data fetched successfully.")
    except Exception as e:
        print("Error fetching candles data:", e)
        return None
    
    df = pd.DataFrame(candles_data)
    
    if 't' in df.columns:
        df['datetime'] = pd.to_datetime(df['t'], unit='ms')
    return df  

if __name__ == "__main__":
    load_dotenv()
    # 例としてBTCの5分足、過去3日分のデータを取得
    symbol = "BTC"
    interval = "5m"
    df_candles = fetch_candles(symbol, interval, days=3)
    if df_candles is not None:
        print("DataFrame Head:")
        print(df_candles.head()) 

    

    
    
     
     
    