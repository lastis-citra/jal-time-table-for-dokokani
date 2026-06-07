# JAL国内線時刻表 スクレイピングツール

羽田空港発の複数の目的地への航空便の時刻表を、時間帯ごとに分類して取得するツールです。

## 使用方法

### 基本的な実行

```bash
python main.py
```

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

## 複数の空港のデータを取得する方法

現在、このツールは `.airport_cache` ディレクトリ内の HTML ファイルからデータを読み込みます。

### ステップ1: キャッシュディレクトリを確認

`.airport_cache` ディレクトリが存在しない場合は作成されます。

### ステップ2: ブラウザからHTMLを取得

1. ブラウザで以下の URL にアクセス（AIRPORT_CODE を置き換えてください）:
   ```
   https://www.jal.co.jp/jp/ja/dom/route/time/timeTable.html?departure=HND&arrival=AIRPORT_CODE&month=20260701_20260831
   ```

2. ページ全体のHTMLをコピー（Ctrl+A → Ctrl+C）

3. `cache_manager.py` スクリプトを使用して保存

### ステップ3: キャッシュを保存

#### 方法A: Python スクリプトを使用

```python
# cache_manager.py を編集して以下のコードを追加
create_cache_for_airport('CTS', '取得したHTMLコンテンツ')
```

#### 方法B: 直接ファイルに保存

1. `.airport_cache` ディレクトリに移動
2. テキストエディタで新規ファイルを作成
3. ファイル名を `AIRPORT_CODE.html` にして保存（例: `CTS.html`）
4. ブラウザからコピーしたHTMLを貼り付け

## ファイル構成

```
.
├── main.py                    # メインスクリプト
├── cache_manager.py           # キャッシュ管理ツール
├── airport_list.conf          # 空港コードのリスト
├── airport_list_test.conf     # テスト用の空港リスト
└── .airport_cache/            # キャッシュディレクトリ
    ├── MYJ.html
    ├── CTS.html
    └── ...
```

## 注意事項

- JAL の Webサイトは JavaScript で動的にレンダリングされているため、直接の HTTP リクエストでは完全なHTMLを取得できません
- キャッシュディレクトリからのデータ読み込みを使用しているため、事前にブラウザからHTMLを取得する必要があります
- 複数の空港を処理する場合は、各空港のHTMLをキャッシュディレクトリに保存してください

## ライセンス

MIT License

## 参考資料

- JAL国内線時刻表: https://www.jal.co.jp/
