from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import datetime
import re
import requests
import csv
from bs4 import BeautifulSoup
import os

def clean_text(text):
    if isinstance(text, str):
        return text.encode('utf-8', 'ignore').decode('utf-8')
    return text

import random
import concurrent.futures
import math
from dateutil.relativedelta import relativedelta

def generate_monthly_ranges(start_date: str, end_date: str) -> list:
    """
    시작일과 종료일 사이의 월별 날짜 범위 리스트 반환
    예: 2019-01-01 ~ 2019-03-15 → [(2019-01-01, 2019-01-31), (2019-02-01, 2019-02-28), (2019-03-01, 2019-03-15)]
    """
    from datetime import datetime
    import calendar

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    ranges = []
    current = start

    while current <= end:
        # 현재 월의 마지막 날
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = current.replace(day=last_day)

        # 종료일이 이번 달 안에 있으면 종료일로
        if month_end > end:
            month_end = end

        # 시작일이 현재 월의 1일이 아닐 수 있음 (첫 달)
        month_start = current

        ranges.append((month_start.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d")))

        # 다음 달 1일로 이동
        current = (month_end + relativedelta(days=1))

    return ranges

def sanitize_filename(s):
    return re.sub(r'[^\w\d_]', '_', s)[:30]

def create_driver():
    """Chrome driver 생성 (재사용용)"""
    chrome_options = Options()
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--lang=ko-KR')
    chrome_options.add_argument('--window-size=1280,800')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=chrome_options)


def get_blog_urls_from_section(driver, keyword, start_date=None, end_date=None, target_count=105):
    """
    블로그 검색 결과에서 URL 수집
    - driver: 외부에서 전달받은 Chrome driver (재사용)
    - 광고 키워드가 제목에 있으면 스킵
    - target_count개 수집되면 종료
    - 최대 100페이지까지만 순회 (무한루프 방지)
    """
    urls = []

    # 광고 키워드 (제목에 있으면 스킵)
    ad_keywords = ['잘보는', '용한곳', '용한 곳', '유명한곳', '유명한 곳', '점잘보는', '점 잘보는',
                   '사주잘보는', '타로잘보는', '후기모음', '추천순위', '가격비교', '할인']

    max_pages_limit = 100  # 무한루프 방지
    page = 1
    skipped_ads = 0

    while len(urls) < target_count and page <= max_pages_limit:
        if start_date and end_date:
            url = f"https://section.blog.naver.com/Search/Post.naver?pageNo={page}&rangeType=PERIOD&orderBy=sim&startDate={start_date}&endDate={end_date}&keyword={keyword}"
        else:
            url = f"https://section.blog.naver.com/Search/Post.naver?pageNo={page}&rangeType=ALL&orderBy=sim&keyword={keyword}"

        driver.get(url)
        time.sleep(1.2)

        # 각 검색 결과 항목 순회
        items = driver.find_elements(By.CSS_SELECTOR, "div.list_search_post > div")

        if not items:
            print(f"  페이지 {page}: 검색 결과 없음, 종료")
            break

        page_urls = 0
        page_skipped = 0

        for item in items:
            if len(urls) >= target_count:
                break

            try:
                # 제목 추출
                title_elem = item.find_element(By.CSS_SELECTOR, "a.desc_inner")
                title_text = title_elem.text if title_elem else ""

                # 광고 키워드 체크
                is_ad = any(ad_kw in title_text for ad_kw in ad_keywords)

                if is_ad:
                    page_skipped += 1
                    skipped_ads += 1
                    continue

                # URL 추출
                href = title_elem.get_attribute("href")
                if href and re.match(r"https://blog\.naver\.com/[^/]+/\d+", href):
                    urls.append(href)
                    page_urls += 1

            except Exception:
                continue

        print(f"  페이지 {page}: {page_urls}개 수집, {page_skipped}개 광고 스킵 (총 {len(urls)}개/{target_count}개 목표)")

        page += 1

    print(f"    [결과] 총 {len(urls)}개 URL 수집 (광고 {skipped_ads}개 스킵)")
    return list(set(urls))

def parse_blog_detail_requests(args):
    url, kw, searchspan, monthlyamount = args
    time.sleep(random.uniform(1.2, 2.0))
    data = {
        'url': url,
        'title': '',
        'content': '',
        'date': '',
        'keyword': kw,
        'searchspan': searchspan,
        'monthlyamount': monthlyamount
    }
    try:
        m = re.match(r"https://blog\.naver\.com/([^/]+)/(\d+)", url)
        if not m:
            return None  # 잘못된 URL은 None 반환

        blogId, logNo = m.groups()

        iframe_url = f"https://blog.naver.com/PostView.naver?blogId={blogId}&logNo={logNo}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://blog.naver.com"
        }
        res = requests.get(iframe_url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        title_sel = soup.select_one("h3.se_textarea, div.se-title-text, span.pcol1.itemSubjectBoldfont")
        if title_sel:
            data['title'] = title_sel.get_text(strip=True)

        content_sel = soup.select_one(
            "div.se-main-container, div#postViewArea, div#contentArea, div#viewTypeSelector, div[data-post-body], article"
        )
        if content_sel:
            content = content_sel.get_text("\n", strip=True)

            # 32,000자 제한 - 최우선 처리
            if len(content) > 32000:
                print(f"[SKIP] 32,000자 초과 글 발견: {len(content)}자 - {url}")
                return None  # 이 글은 아예 수집하지 않음

            data['content'] = content

        date_sel = soup.select_one("span.se_publishDate, span.se-date, span.tdate")
        if date_sel:
            data['date'] = date_sel.get_text(strip=True)

    except Exception as e:
        print(f"[ERROR] {url} - {e}")
        return None

    return data

if __name__ == "__main__":
    excel_file = "search_tasks.xlsx"
    try:
        df_jobs = pd.read_excel(excel_file)
    except Exception as e:
        print(f"[ERROR] 엑셀 파일 '{excel_file}' 로딩 실패: {e}")
        exit()

    # blog_data 폴더 생성
    output_folder = "blog_data"
    os.makedirs(output_folder, exist_ok=True)

    for idx, row in df_jobs.iterrows():
        if pd.isna(row["keywords"]):
            continue

        # pages가 NaN이면 None (자동 계산)
        pages = int(row["pages"]) if "pages" in row and pd.notna(row["pages"]) else None

        keywords = [k.strip() for k in str(row["keywords"]).split(",") if k.strip()]
        if not keywords:
            continue

        # 날짜 범위 읽기 (시간 부분 제거, 날짜만 추출)
        start_date = None
        end_date = None
        if "startDate" in row and pd.notna(row.get("startDate")):
            sd = str(row["startDate"]).strip()
            start_date = sd.split(" ")[0] if " " in sd else sd  # "2025-01-01 00:00:00" → "2025-01-01"
        if "endDate" in row and pd.notna(row.get("endDate")):
            ed = str(row["endDate"]).strip()
            end_date = ed.split(" ")[0] if " " in ed else ed

        date_info = f" | 기간: {start_date} ~ {end_date}" if start_date and end_date else " | 기간: 전체"
        print(f"\n=== [작업 {idx+1}] 키워드: {keywords}{date_info} ===")
        all_results = []

        # Chrome driver 생성 (키워드 단위로 재사용)
        print("\n[INFO] Chrome driver 시작...")
        driver = create_driver()

        for kw in keywords:
            print(f"\n[INFO] '{kw}' 블로그 검색 시작...")

            # 월별로 쪼개서 수집 (기간이 있는 경우)
            # (url, searchspan, monthlyamount) 형태로 저장
            blog_url_data = []
            monthly_summary = []  # 월별 통계용

            if start_date and end_date:
                monthly_ranges = generate_monthly_ranges(start_date, end_date)
                print(f"  → {len(monthly_ranges)}개월로 분할 수집 (월별 105개 목표)")

                for m_idx, (m_start, m_end) in enumerate(monthly_ranges):
                    print(f"\n  [{m_idx+1}/{len(monthly_ranges)}] {m_start} ~ {m_end}")
                    month_urls = get_blog_urls_from_section(driver, kw, start_date=m_start, end_date=m_end, target_count=105)

                    # searchspan: yyyy-mm 형식
                    searchspan = m_start[:7]  # "2019-01-01" → "2019-01"
                    monthlyamount = len(month_urls)

                    # 월별 통계 기록
                    monthly_summary.append({'searchspan': searchspan, 'monthlyamount': monthlyamount})

                    for u in month_urls:
                        blog_url_data.append((u, searchspan, monthlyamount))

                    print(f"    → 이번 달: {monthlyamount}개, 누적: {len(blog_url_data)}개")

            else:
                # 기간 없으면 기존 방식 (전체 기간에서 105개)
                month_urls = get_blog_urls_from_section(driver, kw, target_count=105)
                for u in month_urls:
                    blog_url_data.append((u, "N/A", len(month_urls)))
                monthly_summary.append({'searchspan': 'ALL', 'monthlyamount': len(month_urls)})

            # URL 기준 중복 제거 (첫 번째 것 유지)
            seen_urls = set()
            unique_url_data = []
            for u, span, amt in blog_url_data:
                if u not in seen_urls:
                    seen_urls.add(u)
                    unique_url_data.append((u, span, amt))

            print(f"\n - Found {len(unique_url_data)} URLs (중복 제거 후). 본문 추출 시작...")

            processed_count = 0
            total_urls = len(unique_url_data)

            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
                results = executor.map(parse_blog_detail_requests, [(u, kw, span, amt) for u, span, amt in unique_url_data])
                for detail in results:
                    processed_count += 1
                    if detail is not None:  # None은 32,000자 초과 또는 오류 글
                        all_results.append(detail)
                        print(f"[{processed_count:4d}/{total_urls}] ✓ 수집 성공: {len(all_results)}개 누적")
                    else:
                        print(f"[{processed_count:4d}/{total_urls}] ✗ 스킵 (32k+ 또는 오류)")

                    # 10개마다 진행률 표시
                    if processed_count % 10 == 0:
                        progress = (processed_count / total_urls) * 100
                        print(f"    >>> 진행률: {progress:.1f}% ({processed_count}/{total_urls})")

        # Chrome driver 종료
        driver.quit()
        print("\n[INFO] Chrome driver 종료")

        print(f"\n[INFO] 32,000자 제한 통과한 글: {len(all_results)}개")

        if len(all_results) == 0:
            print("[WARNING] 수집된 데이터가 없습니다. 다음 작업으로 넘어갑니다.")
            continue

        df = pd.DataFrame(all_results)

        # content 열의 깨진 문자 정제
        df['content'] = df['content'].apply(clean_text)

        # title 이후 ~ date 직전 content 범위에서 콤마 제거
        def clean_commas_between_title_and_date(title, content, date):
            if not all(isinstance(x, str) for x in [title, content, date]):
                return content
            combined = title + content + date
            title_index = len(title)
            date_index = combined.find(date)
            if date_index == -1 or title_index >= date_index:
                return content
            before = content[:date_index - title_index].replace(",", "")
            after = content[date_index - title_index:]
            return before + after

        df['content'] = df.apply(lambda row: clean_commas_between_title_and_date(row['title'], row['content'], row['date']), axis=1)

        df['title_head'] = df['title'].str[:30]
        df['content_head'] = df['content'].str[:30]
        df = df.drop_duplicates(subset=['title_head', 'content_head'])
        df = df.drop(columns=['title_head', 'content_head'])
        df = df.drop_duplicates(subset=["url"])

        # URL이 http로 시작하지 않는 행 제거
        df = df[df["url"].apply(lambda x: isinstance(x, str) and x.strip().startswith("http"))]

        now = datetime.datetime.now()
        datestr = now.strftime("%y%m%d%H%M")
        search_part = "_".join([sanitize_filename(kw) for kw in keywords])

        # 날짜 범위를 파일명에 포함
        if start_date and end_date:
            # 날짜 형식 변환 (2024-01-01 → 240101)
            start_short = start_date.replace("-", "")[2:] if "-" in start_date else start_date
            end_short = end_date.replace("-", "")[2:] if "-" in end_date else end_date
            filename = f"naverblog_section_{search_part}_{datestr}_sd{start_short}_ed{end_short}.csv"
        else:
            filename = f"naverblog_section_{search_part}_{datestr}.csv"

        filepath = os.path.join(output_folder, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)

        # 월별 통계 summary CSV 저장
        if monthly_summary:
            summary_filename = filename.replace(".csv", "_summary.csv")
            summary_filepath = os.path.join(output_folder, summary_filename)
            summary_df = pd.DataFrame(monthly_summary)
            summary_df.to_csv(summary_filepath, index=False, encoding="utf-8-sig")
            print(f"\n[✔ 완료] 메인: {filepath} | 수집 건수: {len(df)}")
            print(f"[✔ 완료] 통계: {summary_filepath} | {len(monthly_summary)}개월")
        else:
            print(f"\n[✔ 완료] 파일명: {filepath} | 수집 건수: {len(df)}")
