import re
from bs4 import BeautifulSoup
import sys
import os

def load_airport_list(config_file="airport_list.conf"):
    """設定ファイルから空港リストを読み込む"""
    airports = []
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                airport = line.strip()
                if airport and not airport.startswith('#'):  # 空白行とコメント行をスキップ
                    airports.append(airport)
    return airports

def scrape_flights_from_html(html):
    """HTMLから時刻情報を抽出"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # テーブルから時刻情報を抽出
    table = soup.find('table')
    if not table:
        return None
    
    rows = table.find_all('tr')
    flights = {
        '5-8': [], '9-11': [], '12-15': [], '16-18': [], '19-23': []
    }
    
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) >= 3:
            departure = cells[1].get_text(strip=True)
            arrival = cells[2].get_text(strip=True)
            
            if departure and arrival:
                dep_match = re.search(r'(\d{2}):(\d{2})', departure)
                arr_match = re.search(r'(\d{2}):(\d{2})', arrival)
                
                if dep_match and arr_match:
                    dep_hour = int(dep_match.group(1))
                    dep_formatted = f"{dep_match.group(1)}{dep_match.group(2)}"
                    arr_formatted = f"{arr_match.group(1)}{arr_match.group(2)}"
                    time_str = f"{dep_formatted}-{arr_formatted}"
                    
                    if 5 <= dep_hour <= 8:
                        flights['5-8'].append(time_str)
                    elif 9 <= dep_hour <= 11:
                        flights['9-11'].append(time_str)
                    elif 12 <= dep_hour <= 15:
                        flights['12-15'].append(time_str)
                    elif 16 <= dep_hour <= 18:
                        flights['16-18'].append(time_str)
                    elif 19 <= dep_hour <= 23:
                        flights['19-23'].append(time_str)
    
    return flights

def get_airport_schedule_from_cache(airport_code):
    """キャッシュディレクトリからデータを読み込む"""
    cache_dir = ".airport_cache"
    if not os.path.exists(cache_dir):
        return None
    
    cache_file = os.path.join(cache_dir, f"{airport_code}.html")
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            html = f.read()
        return scrape_flights_from_html(html)
    return None

def format_results(flights):
    """時刻データをタブ区切りでフォーマット"""
    if flights is None:
        return None
    
    result = []
    for key in ['5-8', '9-11', '12-15', '16-18', '19-23']:
        times = ','.join(flights[key])
        result.append(times)
    return '\t'.join(result)

# スタティックデータ
STATIC_DATA = {
    'MYJ': [
        ("06:50", "08:10"),  # JAL 431 - 5時台発
        ("09:30", "10:55"),  # JAL 433 - 9時台発
        ("12:05", "13:30"),  # JAL 435 - 12時台発
        ("15:30", "16:55"),  # JAL 437 - 15時台発
        ("16:45", "18:10"),  # JAL 439 - 16時台発
        ("19:50", "21:10"),  # JAL 443 - 19時台発
    ]
}

def format_static_data(flight_data):
    """スタティックデータから時刻情報を抽出"""
    flights = {
        '5-8': [], '9-11': [], '12-15': [], '16-18': [], '19-23': []
    }
    
    for departure, arrival in flight_data:
        dep_parts = departure.split(':')
        arr_parts = arrival.split(':')
        
        if len(dep_parts) == 2 and len(arr_parts) == 2:
            dep_hour = int(dep_parts[0])
            dep_formatted = f"{dep_parts[0]}{dep_parts[1]}"
            arr_formatted = f"{arr_parts[0]}{arr_parts[1]}"
            time_str = f"{dep_formatted}-{arr_formatted}"
            
            if 5 <= dep_hour <= 8:
                flights['5-8'].append(time_str)
            elif 9 <= dep_hour <= 11:
                flights['9-11'].append(time_str)
            elif 12 <= dep_hour <= 15:
                flights['12-15'].append(time_str)
            elif 16 <= dep_hour <= 18:
                flights['16-18'].append(time_str)
            elif 19 <= dep_hour <= 23:
                flights['19-23'].append(time_str)
    
    return flights

def main():
    """メイン処理"""
    # 空港リストを読み込む
    airports = load_airport_list("airport_list.conf")
    
    if not airports:
        print("エラー: airport_list.conf が見つかないか、空港リストが空です。")
        return
    
    # 各空港について処理
    for i, airport in enumerate(airports, 1):
        # ステータス表示（標準エラー出力）
        print(f"処理中... ({i}/{len(airports)}) {airport}", file=sys.stderr)
        sys.stderr.flush()
        
        # キャッシュから取得
        flights = get_airport_schedule_from_cache(airport)
        
        if flights is None:
            # スタティックデータがあればそれを使用
            if airport in STATIC_DATA:
                flights = format_static_data(STATIC_DATA[airport])
            else:
                flights = None
        
        if flights is not None:
            # 結果をフォーマット
            result = format_results(flights)
            print(result)

if __name__ == "__main__":
    main()
