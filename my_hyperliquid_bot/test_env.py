import os

from dotenv import load_dotenv

load_dotenv()

# 環境変数からAPIキーと秘密鍵を取得する
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

# 値を確認するためにプリントしてみる
print("API_KEY:", api_key)
print("API_SECRET:", api_secret)