import re
from bs4 import BeautifulSoup
import sys
import os
import argparse
from datetime import date, datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DEP_BUCKET_KEYS = ['5-8', '9-11', '12-15', '16-18', '19-23']
ARR_BUCKET_KEYS = ['5-8', '9-12', '12-15', '16-18', '19-24']


def to_half_width_digits(text):
    """全角数字を半角へ正規化"""
    return text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))


def parse_month_range_env():
    """JAL_MONTH(YYYYMMDD_YYYYMMDD)を日付レンジに変換"""
    month = os.getenv("JAL_MONTH", "20260701_20260831")
    try:
        start_raw, end_raw = month.split('_', 1)
        start_dt = datetime.strptime(start_raw, "%Y%m%d").date()
        end_dt = datetime.strptime(end_raw, "%Y%m%d").date()
        return start_dt, end_dt
    except Exception:
        return date(2026, 7, 1), date(2026, 8, 31)


def parse_boarding_date(value):
    """YYYYMMDD文字列をdateへ変換"""
    if not value:
        return None
    normalized = to_half_width_digits(value.strip())
    return datetime.strptime(normalized, "%Y%m%d").date()


def format_hhmm_from_minutes(total_minutes):
    """分単位をHHMM文字列に変換（24hをまたぐ場合は丸める）"""
    total_minutes = total_minutes % (24 * 60)
    hh = total_minutes // 60
    mm = total_minutes % 60
    return f"{hh:02d}{mm:02d}"


def parse_hhmm_to_minutes(hhmm_text):
    """HH:MM形式を分へ変換"""
    hh, mm = hhmm_text.split(':', 1)
    return int(hh) * 60 + int(mm)


def iter_dates_in_range(start_dt, end_dt):
    """開始日から終了日までの日付を列挙"""
    d = start_dt
    while d <= end_dt:
        yield d
        d += timedelta(days=1)


def parse_date_expression(expr, default_year):
    """備考の日付式を日付集合へ展開（例: 8月1～7・28～31日）"""
    text = to_half_width_digits(expr).replace(' ', '')
    parts = [p for p in text.split('・') if p]
    result = set()
    current_month = None

    cross_month = re.match(r'^(\d{1,2})月(\d{1,2})日?～(\d{1,2})月(\d{1,2})日?$', text)
    if cross_month:
        m1, d1, m2, d2 = map(int, cross_month.groups())
        s = date(default_year, m1, d1)
        e = date(default_year, m2, d2)
        for dt in iter_dates_in_range(s, e):
            result.add(dt)
        return result

    for part in parts:
        part = part.replace('日', '')

        m = re.match(r'^(\d{1,2})月(\d{1,2})～(\d{1,2})$', part)
        if m:
            month, d1, d2 = map(int, m.groups())
            current_month = month
            for day in range(d1, d2 + 1):
                result.add(date(default_year, month, day))
            continue

        m = re.match(r'^(\d{1,2})月(\d{1,2})$', part)
        if m:
            month, day = map(int, m.groups())
            current_month = month
            result.add(date(default_year, month, day))
            continue

        m = re.match(r'^(\d{1,2})～(\d{1,2})$', part)
        if m and current_month is not None:
            d1, d2 = map(int, m.groups())
            for day in range(d1, d2 + 1):
                result.add(date(default_year, current_month, day))
            continue

        m = re.match(r'^(\d{1,2})$', part)
        if m and current_month is not None:
            day = int(m.group(1))
            result.add(date(default_year, current_month, day))
            continue

        m = re.match(r'^(\d{1,2})月(\d{1,2})～(\d{1,2})月(\d{1,2})$', part)
        if m:
            m1, d1, m2, d2 = map(int, m.groups())
            s = date(default_year, m1, d1)
            e = date(default_year, m2, d2)
            for dt in iter_dates_in_range(s, e):
                result.add(dt)

    return result


def split_note_clauses(note):
    """備考を日付句ごとに分解"""
    normalized = to_half_width_digits(note or '')
    starts = list(re.finditer(r'\d{1,2}月\d{1,2}', normalized))
    if not starts:
        return []

    clauses = []
    for i, m in enumerate(starts):
        start = m.start()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(normalized)
        clause = normalized[start:end].strip()
        if clause:
            clauses.append(clause)
    return clauses


def parse_note_clause(clause):
    """1つの備考句を date_expr と action_text に分離"""
    m = re.match(r'^(.+?日)\s*(.*)$', clause)
    if not m:
        return None, clause
    return m.group(1).strip(), m.group(2).strip()


def apply_note_adjustment(dep_min, arr_min, note, boarding_dt, default_year):
    """備考と搭乗日をもとに時刻補正と運航判定を適用"""
    if not note or boarding_dt is None:
        return dep_min, arr_min, True

    clauses = split_note_clauses(note)
    if not clauses:
        return dep_min, arr_min, True

    operate = True
    dep_delta = 0
    arr_delta = 0
    matched_any = False

    for clause in clauses:
        date_expr, action_text = parse_note_clause(clause)
        if not date_expr:
            continue

        date_set = parse_date_expression(date_expr, default_year)
        if boarding_dt not in date_set:
            continue

        matched_any = True
        same_arrival_text = '到着は同時刻' in action_text

        if '運休' in action_text:
            operate = False
        if '運航' in action_text:
            operate = True

        for mins_str, action in re.findall(r'(\d+)分(早発|遅発|早着|遅着)', action_text):
            mins = int(mins_str)
            if action == '早発':
                dep_delta -= mins
                if not same_arrival_text:
                    arr_delta -= mins
            elif action == '遅発':
                dep_delta += mins
                if not same_arrival_text:
                    arr_delta += mins
            elif action == '早着':
                arr_delta -= mins
            elif action == '遅着':
                arr_delta += mins

    if not matched_any:
        return dep_min, arr_min, True
    if not operate:
        return dep_min, arr_min, False
    return dep_min + dep_delta, arr_min + arr_delta, True


def parse_flight_records_from_tables(tables):
    """table要素群から便レコードを抽出（便名/出発/到着/備考）"""
    records = []
    for table in tables:
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            flight_no = cells[0].get_text(strip=True)
            dep_text = cells[1].get_text(strip=True)
            arr_text = cells[2].get_text(strip=True)
            note_text = cells[3].get_text(' ', strip=True) if len(cells) >= 4 else ''

            dep_match = re.search(r'(\d{2}:\d{2})', dep_text)
            arr_match = re.search(r'(\d{2}:\d{2})', arr_text)
            if not dep_match or not arr_match:
                continue

            records.append({
                'flight_no': flight_no,
                'dep_min': parse_hhmm_to_minutes(dep_match.group(1)),
                'arr_min': parse_hhmm_to_minutes(arr_match.group(1)),
                'note': note_text,
            })
    return records


def parse_directional_records_from_html(html):
    """HTMLから方向別の便レコードを抽出"""
    soup = BeautifulSoup(html, 'html.parser')
    dep_tables = soup.select('#JS_depArrData table')
    arr_tables = soup.select('#JS_arrDepData table')

    # 方向別コンテナがないHTML向けフォールバック
    if not dep_tables and not arr_tables:
        all_records = parse_flight_records_from_tables(soup.find_all('table'))
        return {
            'dep_records': all_records,
            'arr_records': all_records,
            'all_records': all_records,
        }

    dep_records = parse_flight_records_from_tables(dep_tables)
    arr_records = parse_flight_records_from_tables(arr_tables)
    all_records = dep_records + arr_records

    return {
        'dep_records': dep_records,
        'arr_records': arr_records,
        'all_records': all_records,
    }


def parse_flight_records_from_html(html):
    """HTMLから便レコードを抽出（後方互換: 全方向まとめ）"""
    return parse_directional_records_from_html(html)['all_records']


def init_bucket_dict(keys):
    """時間帯バケットを初期化"""
    return {k: [] for k in keys}


def flights_from_records(records, direction, boarding_dt, default_year):
    """便レコードから方向別の時間帯データを作成"""
    if direction == 'departure':
        buckets = init_bucket_dict(DEP_BUCKET_KEYS)
    else:
        buckets = init_bucket_dict(ARR_BUCKET_KEYS)

    for rec in records:
        dep_min, arr_min, operate = apply_note_adjustment(
            rec['dep_min'], rec['arr_min'], rec['note'], boarding_dt, default_year
        )
        if not operate:
            continue

        dep_hour = (dep_min % (24 * 60)) // 60
        arr_hour = (arr_min % (24 * 60)) // 60
        time_str = f"{format_hhmm_from_minutes(dep_min)}-{format_hhmm_from_minutes(arr_min)}"

        if direction == 'departure':
            if 5 <= dep_hour <= 8:
                buckets['5-8'].append(time_str)
            elif 9 <= dep_hour <= 11:
                buckets['9-11'].append(time_str)
            elif 12 <= dep_hour <= 15:
                buckets['12-15'].append(time_str)
            elif 16 <= dep_hour <= 18:
                buckets['16-18'].append(time_str)
            elif 19 <= dep_hour <= 23:
                buckets['19-23'].append(time_str)
        else:
            if 5 <= arr_hour <= 8:
                buckets['5-8'].append(time_str)
            elif 9 <= arr_hour <= 12:
                buckets['9-12'].append(time_str)
            elif 12 <= arr_hour <= 15:
                buckets['12-15'].append(time_str)
            elif 16 <= arr_hour <= 18:
                buckets['16-18'].append(time_str)
            elif 19 <= arr_hour <= 23:
                buckets['19-24'].append(time_str)

    return buckets

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
    records = parse_directional_records_from_html(html)['dep_records']
    if not records:
        return None
    start_dt, _ = parse_month_range_env()
    return flights_from_records(records, 'departure', None, start_dt.year)

def build_timetable_url(airport_code):
    """JAL時刻表URL（羽田発）を組み立てる"""
    month = os.getenv("JAL_MONTH", "20260701_20260831")
    departure = os.getenv("JAL_DEPARTURE", "HND")
    return (
        "https://www.jal.co.jp/jp/ja/dom/route/time/timeTable.html"
        f"?departure={departure}&arrival={airport_code}&month={month}"
    )


def get_fetch_params(airport_code):
    """取得パラメータを返す"""
    departure = os.getenv("JAL_DEPARTURE", "HND")
    month = os.getenv("JAL_MONTH", "20260701_20260831")
    return departure, airport_code, month


def get_cache_file_path(airport_code):
    """departure/airport_code/month を含むキャッシュファイルパスを返す"""
    departure, arrival, month = get_fetch_params(airport_code)
    cache_dir = ".airport_cache"
    os.makedirs(cache_dir, exist_ok=True)
    safe_name = f"{departure}_{arrival}_{month}".replace("/", "_")
    return os.path.join(cache_dir, f"{safe_name}.html")


def load_html_from_cache(airport_code):
    """キャッシュから生HTMLを読み込む"""
    cache_file = get_cache_file_path(airport_code)
    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None

    return None


def save_html_to_cache(airport_code, html):
    """生HTMLをキャッシュに保存する"""
    cache_file = get_cache_file_path(airport_code)
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(html)


def create_webdriver():
    """Selenium WebDriverを作成"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 検出回避・安定化オプション
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_argument('--window-size=1920,1080')  # サイズ明示

    # パフォーマンス改善
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    return webdriver.Chrome(options=options, service=Service(ChromeDriverManager().install()))


def scrape_arrivals_from_html(html):
    """HTMLから羽田着の時刻情報を抽出（到着時刻で分類）"""
    records = parse_directional_records_from_html(html)['arr_records']
    if not records:
        return None
    start_dt, _ = parse_month_range_env()
    return flights_from_records(records, 'arrival', None, start_dt.year)


def fetch_airport_html(driver, airport_code):
    """同一URLからHTMLを取得する"""
    url = build_timetable_url(airport_code)
    driver.get(url)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(("css selector", "table"))
    )

    return driver.page_source


def is_empty_schedule(flights):
    """全時間帯が空かどうかを判定"""
    if not flights:
        return True
    return all(len(v) == 0 for v in flights.values())


def get_airport_schedules_with_cache(driver, airport_code):
    """キャッシュ優先でHTMLを取得する"""
    cached_html = load_html_from_cache(airport_code)
    used_cache = cached_html is not None

    if cached_html is not None:
        html = cached_html
    else:
        html = fetch_airport_html(driver, airport_code)
        save_html_to_cache(airport_code, html)

    dep_flights = scrape_flights_from_html(html)
    arr_flights = scrape_arrivals_from_html(html)

    # 既存キャッシュが壊れている/古い場合は1回だけ再取得して自己修復
    if used_cache and is_empty_schedule(dep_flights) and is_empty_schedule(arr_flights):
        html = fetch_airport_html(driver, airport_code)
        save_html_to_cache(airport_code, html)
        dep_flights = scrape_flights_from_html(html)
        arr_flights = scrape_arrivals_from_html(html)

    if dep_flights is None:
        dep_flights = {
            '5-8': [], '9-11': [], '12-15': [], '16-18': [], '19-23': []
        }
    if arr_flights is None:
        arr_flights = {
            '5-8': [], '9-12': [], '12-15': [], '16-18': [], '19-24': []
        }

    return {
        'html': html,
    }

def format_results(flights):
    """羽田発の時刻データをタブ区切りでフォーマット"""
    if flights is None:
        return None

    result = []
    for key in DEP_BUCKET_KEYS:
        times = ','.join(flights[key])
        result.append(times)
    return ' '.join(result)


def format_arrival_results(flights):
    """羽田着の時刻データをタブ区切りでフォーマット"""
    if flights is None:
        return None

    result = []
    for key in ARR_BUCKET_KEYS:
        times = ','.join(flights[key])
        result.append(times)
    return ' '.join(result)

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
    parser = argparse.ArgumentParser(description="JAL時刻表取得ツール")
    parser.add_argument("--departure-date", help="羽田発の搭乗日 (YYYYMMDD)")
    parser.add_argument("--arrival-date", help="羽田着の搭乗日 (YYYYMMDD)")
    args = parser.parse_args()

    dep_date_raw = args.departure_date or os.getenv("JAL_DEPARTURE_BOARDING_DATE")
    arr_date_raw = args.arrival_date or os.getenv("JAL_ARRIVAL_BOARDING_DATE")

    try:
        dep_boarding_dt = parse_boarding_date(dep_date_raw)
        arr_boarding_dt = parse_boarding_date(arr_date_raw)
    except ValueError:
        print("エラー: 搭乗日は YYYYMMDD 形式で指定してください。", file=sys.stderr)
        return

    start_dt, end_dt = parse_month_range_env()
    default_year = start_dt.year

    if dep_boarding_dt is not None and not (start_dt <= dep_boarding_dt <= end_dt):
        print("エラー: --departure-date が JAL_MONTH の範囲外です。", file=sys.stderr)
        return
    else:
        print(f"羽田発の搭乗日: {dep_boarding_dt} (JAL_MONTH: {start_dt}～{end_dt})", file=sys.stderr)
    if arr_boarding_dt is not None and not (start_dt <= arr_boarding_dt <= end_dt):
        print("エラー: --arrival-date が JAL_MONTH の範囲外です。", file=sys.stderr)
        return
    else:
        print(f"羽田着の搭乗日: {arr_boarding_dt} (JAL_MONTH: {start_dt}～{end_dt})", file=sys.stderr)

    # 空港リストを読み込む
    airports = load_airport_list("airport_list.conf")
    
    if not airports:
        print("エラー: airport_list.conf が見つかないか、空港リストが空です。")
        return
    
    try:
        driver = create_webdriver()
    except Exception as e:
        print(f"エラー: WebDriver の初期化に失敗しました: {e}", file=sys.stderr)
        print("Chrome と Selenium が利用可能か確認してください。", file=sys.stderr)
        return

    try:
        dep_output_lines = []
        arr_output_lines = []

        # 各空港について処理
        for i, airport in enumerate(airports, 1):
            # ステータス表示（標準エラー出力）
            print(f"処理中... ({i}/{len(airports)}) {airport}", file=sys.stderr)
            sys.stderr.flush()

            flights_dep = None
            flights_arr = None
            try:
                schedules = get_airport_schedules_with_cache(driver, airport)
                html = schedules.get('html')
                directional = parse_directional_records_from_html(html)
                flights_dep = flights_from_records(directional['dep_records'], 'departure', dep_boarding_dt, default_year)
                flights_arr = flights_from_records(directional['arr_records'], 'arrival', arr_boarding_dt, default_year)
            except Exception as e:
                print(f"警告: {airport} の取得に失敗しました: {e}", file=sys.stderr)

            if flights_dep is None and airport in STATIC_DATA:
                flights_dep = format_static_data(STATIC_DATA[airport])

            if flights_dep is None:
                flights_dep = init_bucket_dict(DEP_BUCKET_KEYS)
            if flights_arr is None:
                flights_arr = init_bucket_dict(ARR_BUCKET_KEYS)

            dep_output_lines.append(format_results(flights_dep))
            arr_output_lines.append(format_arrival_results(flights_arr))

        # 全空港の処理完了後にまとめて標準出力
        print("羽田発")
        for line in dep_output_lines:
            print(line)
        print()
        print("羽田着")
        for line in arr_output_lines:
            print(line)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
