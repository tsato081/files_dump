# Hyperliquid データコレクター

このプログラムはHyperliquidの取引所からリアルタイムデータを収集し、CSVファイルに保存します。

## 収集データ

1. **約定履歴（trades）**: ティックごとの取引履歴
2. **オーダーブック（l2book）**: 板情報（上位5レベルのbidとask）
3. **全中値（allMids）**: 全銘柄の中値データ
4. **オープンインタレスト（open_interest）**: ティックごとのオープンインタレスト

## 必要条件

- Python 3.7以上
- 必要なパッケージ（requirements.txtに記載）

## インストール方法

```bash
# 仮想環境の作成（オプション）
python -m venv .venv
source .venv/bin/activate  # Linuxの場合
# Windows: .venv\Scripts\activate

# 必要なパッケージのインストール
pip install -r requirements.txt
```

## 使用方法

```bash
python hyperliquid_data_collector.py
```

プログラムを実行すると、以下のファイルが`data`ディレクトリに生成されます：

- `trades_YYYYMMDD_HHMMSS.csv`: 約定履歴
- `l2book_YYYYMMDD_HHMMSS.csv`: オーダーブック情報
- `all_mids_YYYYMMDD_HHMMSS.csv`: 全中値情報
- `open_interest_YYYYMMDD_HHMMSS.csv`: オープンインタレスト情報

## 終了方法

実行中のプログラムを終了するには、`Ctrl+C`を押してください。 