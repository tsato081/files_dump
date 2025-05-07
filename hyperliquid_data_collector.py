#!/usr/bin/env python3
import asyncio
import json
import os
import time
import websockets
import aiohttp
import pandas as pd
from datetime import datetime
import csv
import signal
from pathlib import Path

# 定数定義
WS_URL = "wss://api.hyperliquid.xyz/ws"
HTTP_URL = "https://api.hyperliquid.xyz/info"
OUTPUT_DIR = "data"
TARGET_COIN = "BTC"  # 情報収集の対象コイン
OI_FETCH_INTERVAL = 5  # Open Interest取得間隔（秒）

# デバッグモード
DEBUG = True

# 出力ディレクトリの作成
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# データ保存用のファイル名を生成（現在のタイムスタンプを使用）
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
TRADES_FILE = f"{OUTPUT_DIR}/trades_{timestamp}.csv"
BOOK_FILE = f"{OUTPUT_DIR}/l2book_{timestamp}.csv"
MIDS_FILE = f"{OUTPUT_DIR}/all_mids_{timestamp}.csv"
OI_FILE = f"{OUTPUT_DIR}/open_interest_{timestamp}.csv"
DEBUG_FILE = f"{OUTPUT_DIR}/debug_{timestamp}.log"

# 実行終了用のフラグ
running = True

def handle_signal(sig, frame):
    """シグナルハンドラ（Ctrl+Cなど）"""
    global running
    print("シャットダウンシグナルを受信しました。クリーンアップ中...")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def log_debug(message):
    """デバッグログを記録する"""
    if DEBUG:
        timestamp = datetime.now().isoformat()
        with open(DEBUG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"[DEBUG] {message}")

async def get_btc_open_interest():
    """HTTP APIを使用してBTCのOpen Interestデータを取得する"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                HTTP_URL,
                json={"type": "metaAndAssetCtxs"},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # データ構造の確認
                    if isinstance(data, list) and len(data) >= 2:
                        meta_data = data[0]
                        asset_ctx_data = data[1]
                        
                        # metaデータから銘柄インデックスを取得
                        btc_index = -1
                        if isinstance(meta_data, dict) and "universe" in meta_data:
                            universe = meta_data.get("universe", [])
                            for i, item in enumerate(universe):
                                if isinstance(item, dict) and item.get("name") == TARGET_COIN:
                                    btc_index = i
                                    break
                        
                        if btc_index >= 0 and btc_index < len(asset_ctx_data):
                            # BTCのデータを取得
                            asset_ctx = asset_ctx_data[btc_index]
                            if isinstance(asset_ctx, dict):
                                open_interest = asset_ctx.get("openInterest", "0")
                                mark_price = asset_ctx.get("markPx", "0")
                                return {
                                    "coin": TARGET_COIN,
                                    "openInterest": open_interest,
                                    "markPrice": mark_price
                                }
                        
                        # インデックスが見つからない場合はすべての資産を検索
                        for asset_ctx in asset_ctx_data:
                            if isinstance(asset_ctx, dict) and asset_ctx.get("coin") == TARGET_COIN:
                                open_interest = asset_ctx.get("openInterest", "0")
                                mark_price = asset_ctx.get("markPx", "0")
                                return {
                                    "coin": TARGET_COIN,
                                    "openInterest": open_interest,
                                    "markPrice": mark_price
                                }
                        
                        # BTCが見つからない場合
                        log_debug(f"BTCのOpen Interestデータが見つかりませんでした。")
                        return None
                    else:
                        log_debug(f"Unexpected API Response Format: {json.dumps(data)[:500]}...")
                else:
                    log_debug(f"API Error Status: {response.status}")
        return None
    except Exception as e:
        log_debug(f"API Request Error: {str(e)}")
        return None

async def subscribe_to_websocket():
    """ウェブソケットに接続し、必要なトピックをサブスクライブする"""
    try:
        log_debug(f"WebSocket接続開始: {WS_URL}")

        # 各データファイルのヘッダーを書き込む
        trades_headers = ["timestamp", "coin", "side", "price", "size", "time", "tid"]
        with open(TRADES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(trades_headers)
        
        book_headers = (
            ["timestamp"] + 
            [f"bid_px_{i}" for i in range(1, 6)] + 
            [f"bid_sz_{i}" for i in range(1, 6)] + 
            [f"ask_px_{i}" for i in range(1, 6)] + 
            [f"ask_sz_{i}" for i in range(1, 6)]
        )
        with open(BOOK_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(book_headers)
        
        mids_headers = ["timestamp", "coin", "mid"]
        with open(MIDS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(mids_headers)
            
        oi_headers = ["timestamp", "coin", "open_interest", "mark_price"]
        with open(OI_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(oi_headers)

        # ウェブソケット接続
        async with websockets.connect(WS_URL) as websocket:
            # トレード情報のサブスクライブ
            log_debug(f"{TARGET_COIN}トレード情報をサブスクライブ中")
            await websocket.send(json.dumps({
                "method": "subscribe", 
                "subscription": {
                    "type": "trades", 
                    "coin": TARGET_COIN
                }
            }))
            
            # オーダーブック（L2）情報のサブスクライブ
            log_debug(f"{TARGET_COIN}オーダーブック情報をサブスクライブ中")
            await websocket.send(json.dumps({
                "method": "subscribe", 
                "subscription": {
                    "type": "l2Book", 
                    "coin": TARGET_COIN
                }
            }))
            
            # BTCの中値情報のサブスクライブ（allMidsの代わりに単一コインの中値を取得）
            log_debug(f"{TARGET_COIN}中値情報をサブスクライブ中")
            await websocket.send(json.dumps({
                "method": "subscribe", 
                "subscription": {
                    "type": "mids", 
                    "coin": TARGET_COIN
                }
            }))

            # サブスクリプション応答の処理
            for _ in range(3):  # 3つのサブスクリプションのレスポンスを待機
                response = await websocket.recv()
                log_debug(f"Subscription Response: {response[:200]}")

            log_debug("WebSocketの受信待機を開始")
            
            # Open Interest情報の初期取得と定期的な更新
            oi_task = asyncio.create_task(fetch_open_interest_periodically())
            
            global running
            message_count = 0
            while running:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    now = datetime.now().isoformat()
                    message_count += 1
                    
                    # デバッグ用：メッセージの構造を出力
                    if message_count <= 5 or message_count % 20 == 0:  # 最初の5つとその後は20メッセージごとに記録
                        if isinstance(data, dict):
                            log_debug(f"WS Message #{message_count} Type: dict, Keys: {list(data.keys())}")
                            if len(message) < 1000:
                                log_debug(f"WS Message Content: {message}")
                            else:
                                log_debug(f"WS Message Content (truncated): {message[:500]}...")
                        elif isinstance(data, list):
                            log_debug(f"WS Message #{message_count} Type: list, Length: {len(data)}")
                            if len(message) < 1000:
                                log_debug(f"WS Message Content: {message}")
                            else:
                                log_debug(f"WS Message Content (truncated): {message[:500]}...")
                        else:
                            log_debug(f"WS Message #{message_count} Type: {type(data)}")
                    
                    # メッセージの形式に応じて処理
                    if isinstance(data, dict) and "channel" in data:
                        channel = data.get("channel")
                        channel_data = data.get("data", {})
                        
                        if channel == "trades":
                            # トレード情報の処理
                            if isinstance(channel_data, list):
                                log_debug(f"受信したトレード数: {len(channel_data)}")
                                for trade in channel_data:
                                    if isinstance(trade, dict):
                                        coin = trade.get("coin", "unknown")
                                        if coin != TARGET_COIN:
                                            continue
                                            
                                        side = trade.get("side", "unknown")
                                        px = trade.get("px", "0")
                                        sz = trade.get("sz", "0")
                                        trade_time = trade.get("time", 0)
                                        tid = trade.get("tid", 0)
                                        
                                        log_debug(f"トレード記録: {coin} {side} {px} {sz}")
                                        with open(TRADES_FILE, 'a', newline='') as f:
                                            writer = csv.writer(f)
                                            writer.writerow([now, coin, side, px, sz, trade_time, tid])
                        
                        elif channel == "l2Book":
                            # オーダーブック情報の処理
                            if isinstance(channel_data, dict):
                                coin = channel_data.get("coin", "unknown")
                                if coin != TARGET_COIN:
                                    continue
                                    
                                levels = channel_data.get("levels", {})
                                
                                if isinstance(levels, list) and len(levels) == 2:
                                    bids = levels[0]  # bidsは最初の配列
                                    asks = levels[1]  # asksは2番目の配列
                                    
                                    log_debug(f"オーダーブック: {len(bids)}件の買い注文と{len(asks)}件の売り注文")
                                    
                                    # 上位5レベルの情報を取得（存在しない場合は0で埋める）
                                    bid_prices = []
                                    bid_sizes = []
                                    ask_prices = []
                                    ask_sizes = []
                                    
                                    for i in range(min(5, len(bids))):
                                        if isinstance(bids[i], dict):
                                            bid_prices.append(bids[i].get("px", "0"))
                                            bid_sizes.append(bids[i].get("sz", "0"))
                                        elif isinstance(bids[i], list) and len(bids[i]) >= 2:
                                            bid_prices.append(bids[i][0])
                                            bid_sizes.append(bids[i][1])
                                    
                                    for i in range(min(5, len(asks))):
                                        if isinstance(asks[i], dict):
                                            ask_prices.append(asks[i].get("px", "0"))
                                            ask_sizes.append(asks[i].get("sz", "0"))
                                        elif isinstance(asks[i], list) and len(asks[i]) >= 2:
                                            ask_prices.append(asks[i][0])
                                            ask_sizes.append(asks[i][1])
                                    
                                    # 不足している場合は0で埋める
                                    bid_prices.extend(["0"] * (5 - len(bid_prices)))
                                    bid_sizes.extend(["0"] * (5 - len(bid_sizes)))
                                    ask_prices.extend(["0"] * (5 - len(ask_prices)))
                                    ask_sizes.extend(["0"] * (5 - len(ask_sizes)))
                                    
                                    # CSVに書き込み
                                    with open(BOOK_FILE, 'a', newline='') as f:
                                        writer = csv.writer(f)
                                        writer.writerow([now] + bid_prices + bid_sizes + ask_prices + ask_sizes)
                        
                        elif channel == "mids":
                            # 中値情報の処理
                            if isinstance(channel_data, dict):
                                coin = channel_data.get("coin", "unknown")
                                if coin != TARGET_COIN:
                                    continue
                                    
                                mid = channel_data.get("mid", "0")
                                log_debug(f"中値記録: {coin} {mid}")
                                with open(MIDS_FILE, 'a', newline='') as f:
                                    writer = csv.writer(f)
                                    writer.writerow([now, coin, mid])
                                    
                        elif channel == "allMids":
                            # 全ての中値情報から対象コインだけを処理
                            if isinstance(channel_data, dict) and "mids" in channel_data:
                                mids_dict = channel_data.get("mids", {})
                                
                                if TARGET_COIN in mids_dict:
                                    mid = mids_dict[TARGET_COIN]
                                    log_debug(f"中値記録: {TARGET_COIN} {mid}")
                                    with open(MIDS_FILE, 'a', newline='') as f:
                                        writer = csv.writer(f)
                                        writer.writerow([now, TARGET_COIN, mid])
                
                except asyncio.TimeoutError:
                    log_debug("WebSocketからの応答タイムアウト。再試行中...")
                    continue
                except websockets.exceptions.ConnectionClosed:
                    log_debug("WebSocket接続が閉じられました。再接続します...")
                    break
                except Exception as e:
                    log_debug(f"ウェブソケット処理中にエラーが発生しました: {str(e)}")
                    if not running:
                        break
                    await asyncio.sleep(1)  # 再接続前に少し待機
            
            # クリーンアップ
            oi_task.cancel()
            try:
                await oi_task
            except asyncio.CancelledError:
                log_debug("Open Interest取得タスクをキャンセルしました")
                
    except Exception as conn_error:
        log_debug(f"WebSocketへの接続中にエラーが発生しました: {str(conn_error)}")

async def fetch_open_interest_periodically():
    """定期的にBTCのOpen Interestデータを取得する"""
    try:
        log_debug("BTC Open Interest定期取得タスク開始")
        while running:
            try:
                now = datetime.now().isoformat()
                log_debug("BTC Open Interest取得開始")
                
                # BTCのOpen Interestデータを取得
                btc_data = await get_btc_open_interest()
                
                if btc_data:
                    coin = btc_data.get("coin", TARGET_COIN)
                    open_interest = btc_data.get("openInterest", "0")
                    mark_price = btc_data.get("markPrice", "0")
                    
                    log_debug(f"Open Interest記録: {coin} {open_interest} {mark_price}")
                    with open(OI_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([now, coin, open_interest, mark_price])
                
                # 次の取得までOI_FETCH_INTERVAL秒待機
                await asyncio.sleep(OI_FETCH_INTERVAL)
            
            except Exception as e:
                log_debug(f"Open Interest取得中にエラーが発生しました: {str(e)}")
                if not running:
                    break
                await asyncio.sleep(2)  # エラー発生時は少し待機
    
    except asyncio.CancelledError:
        log_debug("BTC Open Interest定期取得タスクがキャンセルされました")
        raise
    except Exception as e:
        log_debug(f"BTC Open Interest定期取得タスクでエラーが発生しました: {str(e)}")

async def main():
    """メイン関数"""
    print(f"Hyperliquid {TARGET_COIN}データ収集開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"トレードデータ: {TRADES_FILE}")
    print(f"オーダーブックデータ: {BOOK_FILE}")
    print(f"中値データ: {MIDS_FILE}")
    print(f"オープンインタレストデータ: {OI_FILE}")
    print(f"デバッグログ: {DEBUG_FILE}")
    print("終了するには Ctrl+C を押してください...")
    
    # デバッグヘッダーを書き込む
    with open(DEBUG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] Hyperliquid {TARGET_COIN}データコレクターデバッグログ開始\n")
    
    while running:
        try:
            # WebSocketタスクを実行
            await subscribe_to_websocket()
            
            if running:
                log_debug("接続が切断されました。3秒後に再接続します...")
                await asyncio.sleep(3)
        except Exception as e:
            log_debug(f"予期しないエラーが発生しました: {str(e)}")
            if running:
                log_debug("3秒後に再試行します...")
                await asyncio.sleep(3)
    
    print("データ収集が完了しました。")

if __name__ == "__main__":
    asyncio.run(main()) 