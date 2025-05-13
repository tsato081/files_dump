import os
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

# 環境変数の読み込み
load_dotenv(override=True)

# 固定して直接読み込む
SECRET_KEY = os.getenv("HL_PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("HL_ACCOUNT_ADDRESS")
# .envから読み込むか、なければ定数MAINNET_API_URLを使う
API_URL = os.getenv("MAINNET_API_URL") or MAINNET_API_URL

def main():
    if not SECRET_KEY or not ACCOUNT_ADDRESS or not API_URL:
        raise ValueError(".envファイルに必要な環境変数が不足しています。")
    
    # ウォレットの初期化
    account = Account.from_key(SECRET_KEY)
    
    # Infoクラスのインスタンス作成（口座情報確認用）
    info = Info(base_url=API_URL, skip_ws=True)
    
    # Exchangeクラスのインスタンス作成（注文発注用）
    exchange = Exchange(account, base_url=API_URL, account_address=ACCOUNT_ADDRESS)
    
    # ユーザーのスポット口座の状態を確認（残高など）
    spot_state = info.spot_user_state(ACCOUNT_ADDRESS)
    print("スポット口座の状態:")
    print(spot_state)
    
    
    COIN_PAIR = "XRP"   # 取引所に合わせたペア名に変更してください
    IS_BUY = True            # 買い注文
    SIZE = 4                 # 1 XRP
    # マーケット注文の場合、limit_pxは不要なので0に設定
    LIMIT_PRICE = 2.704      
    ORDER_TYPE = {"limit": {"tif": "Ioc"}}  # マーケット注文の設定
    
    print("マーケット注文を発注中...")
    order_result = exchange.order(COIN_PAIR, IS_BUY, SIZE, LIMIT_PRICE, ORDER_TYPE)
    print("注文発注レスポンス:")
    print(order_result)
    
    # 注文結果のステータス確認
    if order_result.get("status") == "ok":
        try:
            statuses = order_result["response"]["data"]["statuses"]
            if statuses:
                status_item = statuses[0]
                oid = None
                if "resting" in status_item:
                    oid = status_item["resting"].get("oid")
                elif "filled" in status_item:
                    oid = status_item["filled"].get("oid")
                if oid:
                    order_status = info.query_order_by_oid(ACCOUNT_ADDRESS, oid)
                    print("注文ステータス:")
                    print(order_status)
                else:
                    print("注文IDが取得できませんでした。")
            else:
                print("注文のステータス情報が空です。")
        except Exception as e:
            print("注文ステータスの確認中にエラー:", e)
    else:
        print("注文発注にエラーが発生しました。")

if __name__ == "__main__":
    main()



#仕様的に、マーケット注文をする時はlimitを近づけて