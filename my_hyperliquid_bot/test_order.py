import os
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

# 環境変数を読み込み
load_dotenv(override=True)

# メインネット用の環境変数を直接読み込む
SECRET_KEY = os.getenv("HL_PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("HL_ACCOUNT_ADDRESS")
API_URL = "https://api.hyperliquid.xyz"


print("API_URL:", API_URL)

def main():
    if not SECRET_KEY or not ACCOUNT_ADDRESS or not API_URL:
        raise ValueError(".envファイルに必要な環境変数が不足しています。")

    # ウォレットの初期化
    account = Account.from_key(SECRET_KEY)
    # Infoクラスのインスタンス作成
    info = Info(base_url=API_URL, skip_ws=True)
    # Exchangeクラスのインスタンス作成
    exchange = Exchange(account, base_url=API_URL, account_address=ACCOUNT_ADDRESS)

    # ユーザーのスポット残高を確認
    spot_user_state = info.spot_user_state(ACCOUNT_ADDRESS)
    balances = spot_user_state.get("balances", [])
    if balances:
        print("スポット残高:")
        for balance in balances:
            print(balance)
    else:
        print("利用可能なスポット残高がありません。")
        print("DEBUG: spot_user_state:", spot_user_state)
        print("DEBUG: ACCOUNT_ADDRESS:", ACCOUNT_ADDRESS)

    # スポット注文の設定：XRP/USDC ペアで1 XRPの買い注文
    COIN_PAIR = "XRP"   # ご利用の取引所に合わせたペア名に調整してください
    IS_BUY = True            # 買い注文
    SIZE = 4            # 1 XRP
    # 市場価格近くのリミット注文を発注する場合、現在の市場価格に近い価格を設定してください。
    # ここでは例として 0.50 USDC を設定しています（実際の価格に合わせてください）。
    LIMIT_PRICE = 2.7115  
    ORDER_TYPE = {"limit": {"tif": "Gtc"}}  # Gtc: Good Till Canceled

    print("XRP買い注文を送信中...")
    order_result = exchange.order(COIN_PAIR, IS_BUY, SIZE, LIMIT_PRICE, ORDER_TYPE)
    print("注文結果:", order_result)

    # 注文ステータスを確認する例
    if order_result.get("status") == "ok":
        try:
            status = order_result["response"]["data"]["statuses"][0]
            oid = status.get("resting", {}).get("oid")
            if oid:
                order_status = info.query_order_by_oid(ACCOUNT_ADDRESS, oid)
                print("注文ステータス:", order_status)
            else:
                print("注文IDが取得できませんでした。")
        except Exception as e:
            print("注文ステータスの確認中にエラー:", e)
    else:
        print("注文にエラーが発生しました。")

if __name__ == "__main__":
    main()
