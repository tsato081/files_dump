from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL
from dotenv import load_dotenv
import os
import time

load_dotenv(override=True)

SECRET_KEY = os.getenv("HL_PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("HL_ACCOUNT_ADDRESS")
API_URL = 'https://api.hyperliquid.xyz'

print(SECRET_KEY)
print(ACCOUNT_ADDRESS)
print(API_URL)


def main():
    if not SECRET_KEY or not ACCOUNT_ADDRESS or not API_URL:
        raise ValueError(".envファイルに必要な環境変数が不足しています。")
    
    # ウォレットの初期化
    account = Account.from_key(SECRET_KEY)
    # Infoクラスのインスタンス作成（口座情報確認用）
    info = Info(base_url=API_URL, skip_ws=True)
    # Exchangeクラスのインスタンス作成（注文発注用）
    exchange = Exchange(account, base_url=API_URL, account_address=ACCOUNT_ADDRESS)
    
    # ユーザーのスポット口座の状態を確認
    spot_state = info.spot_user_state(ACCOUNT_ADDRESS)
    print("スポット口座の状態:")
    print(spot_state)
    
    # 注文の例
    # ここでは例として、ETHのマーケット注文を発注します
    # 公式例では、market_open() を使って注文発注しているので、同様にします。
    coin = "XRP"          # 注文する銘柄（ここではETH）
    is_buy = False        # Falseの場合、売り注文（買い注文ならTrue）
    sz = 4            # 注文サイズ（例：0.05 ETH）
    
    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {sz} {coin}.")
    
    # market_open() の第4引数に None、第5引数にスリッページを指定しています
    order_result = exchange.market_open(coin, is_buy, sz, None, 0.01)
    print("注文発注レスポンス:")
    print(order_result)
    
    # 注文ステータスの確認
    if order_result.get("status") == "ok":
        try:
            statuses = order_result["response"]["data"]["statuses"]
            if statuses:
                # 注文IDは filled セクションにある場合もあるのでチェックします
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
