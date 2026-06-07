"""
JAL時刻表をブラウザから取得してキャッシュに保存するツール
複数の空港のHTMLデータを .airport_cache ディレクトリに保存します
"""
import os
import sys

def create_cache_for_airport(airport_code, html_content):
    """HTMLコンテンツをキャッシュディレクトリに保存"""
    cache_dir = ".airport_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    cache_file = os.path.join(cache_dir, f"{airport_code}.html")
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✓ {airport_code} を保存しました")

def create_cache_from_browser_data():
    """ブラウザから取得したHTMLデータを保存
    
    使用方法:
    1. ブラウザで各空港のURLにアクセス
       https://www.jal.co.jp/jp/ja/dom/route/time/timeTable.html?departure=HND&arrival=AIRPORT_CODE&month=20260701_20260831
    2. ページのHTML全体をコピーして、下記の対応する部分に貼り付け
    3. このスクリプトを実行
    """
    
    # サンプル: ブラウザから取得したHTMLを変数に保存
    # 実際のHTMLコンテンツに置き換えてください
    
    print("ブラウザからHTMLデータをコピーして保存してください")
    print("format: create_cache_for_airport('AIRPORT_CODE', 'HTML_CONTENT')")
    print("\n例:")
    print("create_cache_for_airport('CTS', '''<html>...</html>''')")

def save_sample_cache():
    """サンプル用のキャッシュを作成（MYJのみ）"""
    cache_dir = ".airport_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # サンプルのMYJ HTMLデータ
    myj_html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <title>JAL国内線時刻表</title>
</head>
<body>
<table>
    <thead>
        <tr>
            <th>便名</th>
            <th>出発</th>
            <th>到着</th>
            <th>備考</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>JAL 431</td>
            <td>06:50</td>
            <td>08:10</td>
            <td></td>
        </tr>
        <tr>
            <td>JAL 433</td>
            <td>09:30</td>
            <td>10:55</td>
            <td></td>
        </tr>
        <tr>
            <td>JAL 435</td>
            <td>12:05</td>
            <td>13:30</td>
            <td>8月1～31日5分遅発</td>
        </tr>
        <tr>
            <td>JAL 437</td>
            <td>15:30</td>
            <td>16:55</td>
            <td></td>
        </tr>
        <tr>
            <td>JAL 439</td>
            <td>16:45</td>
            <td>18:10</td>
            <td>7月1～31日10分遅発</td>
        </tr>
        <tr>
            <td>JAL 443</td>
            <td>19:50</td>
            <td>21:10</td>
            <td>8月1～7日5分遅着</td>
        </tr>
    </tbody>
</table>
</body>
</html>"""
    
    create_cache_for_airport('MYJ', myj_html)
    print("\nサンプルキャッシュを作成しました")
    print("他の空港のHTMLデータをブラウザから取得して、キャッシュディレクトリに保存してください")

if __name__ == "__main__":
    print("JAL時刻表 キャッシュ生成ツール\n")
    save_sample_cache()
