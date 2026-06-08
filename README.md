# JAL国内線時刻表 スクレイピングツール

羽田空港発の複数の目的地への航空便の時刻表を、時間帯ごとに分類して取得するツールです。

## 使用方法

### 基本的な実行

```bash
python main.py
```

Selenium で JAL サイトを動的取得して解析します。

### 日付指定オプション（備考反映）

備考欄の「早発・遅発・早着・遅着・運休」を反映する場合は、搭乗日を指定して実行します。

```bash
python main.py --departure-date 20260710 --arrival-date 20260830
```

- `--departure-date`: 羽田発の搭乗日（`YYYYMMDD`）
- `--arrival-date`: 羽田着の搭乗日（`YYYYMMDD`）

どちらも省略可能です。省略時は時刻補正なしで出力します。

### 出力形式

タブ区切りで以下の形式で出力されます：

```
5～8時台発	9～11時台発	12～15時台発	16～18時台発	19～23時台発
0650-0810	0930-1055	1205-1330,1530-1655	1645-1810	1950-2110
```

複数の空港がある場合は、空港ごとに改行して出力されます。

## 設定

### airport_list.conf

`airport_list.conf` ファイルに、処理対象の空港コードを1行ずつ記載します。

例：
```
CTS  # 新千歳空港（札幌）
MYJ  # 松山空港
KIX  # 関西国際空港
```

## 動作要件

- Google Chrome がインストールされていること
- `selenium` がインストールされていること

Selenium 4.6 以降では Selenium Manager により ChromeDriver は自動解決されます。

## 環境変数

- `JAL_DEPARTURE`: 出発空港コード（既定値: `HND`）
- `JAL_MONTH`: 対象月パラメータ（既定値: `20260701_20260831`）
- `JAL_DEPARTURE_BOARDING_DATE`: 羽田発の搭乗日（`YYYYMMDD`）
- `JAL_ARRIVAL_BOARDING_DATE`: 羽田着の搭乗日（`YYYYMMDD`）

例:

```bash
set JAL_DEPARTURE=HND
set JAL_MONTH=20260701_20260831
set JAL_DEPARTURE_BOARDING_DATE=20260710
set JAL_ARRIVAL_BOARDING_DATE=20260830
python main.py
```

## ファイル構成

```
.
├── main.py                    # メインスクリプト
├── airport_list.conf          # 空港コードのリスト
├── pyproject.toml             # 依存関係定義
├── uv.lock                    # lockファイル
└── README.md                  # このドキュメント
```

## 注意事項

- JAL の Webサイトは JavaScript で動的にレンダリングされるため、Selenium による取得が必要です
- ネットワーク状況やサイト構造変更により、取得が失敗する場合があります

## ライセンス

MIT License

## 参考資料

- JAL国内線時刻表: https://www.jal.co.jp/
