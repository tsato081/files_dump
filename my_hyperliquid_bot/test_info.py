import os
from dotenv import load_dotenv
from hyperliquid.info import Info

# .envファイルの読み込み
load_dotenv()

# 必要に応じて base_url を指定
# ※ 基本的には公式のエンドポイントに合わせるか、SDKのデフォルトが利用されるはずです。
client = Info(base_url="https://api.hyperliquid.xyz")



user_address = os.getenv("MAIN_ACCOUNT_ADDRESS")
if user_address:
    print("\n=== User State ===")
    try:
        user_state = client.user_state(user_address)
        print(user_state)
    except Exception as e:
        print("User state 取得中にエラー:", e)
else:
    print("\n.env に HL_ACCOUNT_ADDRESS が設定されていません。")
    
# --- テスト3: open orders の取得 ---
if user_address:
    print("\n=== Open Orders ===")
    try:
        orders = client.open_orders(user_address)
        print(orders)
    except Exception as e:
        print("Open orders 取得中にエラー:", e)
else:
    print("User address がないので open orders はスキップします。")


