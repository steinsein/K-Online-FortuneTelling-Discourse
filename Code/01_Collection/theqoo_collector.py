"""
더쿠(theqoo.net) 전체 게시판 검색 크롤러
- 수동 로그인 후 검색 기능 활용
- 키워드별 URL/제목/본문/작성일/조회수 수집
- Excel 저장 + 비프음 알림
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import winsound
from datetime import datetime
from urllib.parse import quote, urlencode


# ──────────────────────────── 설정 ────────────────────────────
SITE = "https://theqoo.net"
DELAY_PAGE = (2, 4)       # 목록 페이지 간 딜레이 (초)
DELAY_POST = (1.5, 3)     # 게시글 접속 간 딜레이 (초)
SAVE_EVERY = 50           # N개마다 중간 저장


# ──────────────────────────── 브라우저 설정 ────────────────────
def create_driver():
    opts = webdriver.ChromeOptions()

    # 자동화 탐지 회피
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    opts.add_argument(f"user-agent={random.choice(user_agents)}")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    })
    return driver


# ──────────────────────────── 유틸 ─────────────────────────────
def delay(range_tuple):
    time.sleep(random.uniform(*range_tuple))


def beep():
    """키워드 수집 완료 알림음"""
    for _ in range(3):
        winsound.Beep(800, 300)
        time.sleep(0.15)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def save_excel(rows, keyword):
    """Excel 저장 — 키워드별 파일"""
    if not rows:
        log(f"'{keyword}' 수집 결과가 없어 저장을 건너뜁니다.")
        return None
    df = pd.DataFrame(rows)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"theqoo_{keyword}_{date_str}.xlsx"
    df.to_excel(fname, index=False, engine="openpyxl")
    log(f"저장 완료: {fname} ({len(rows)}건)")
    return fname


# ──────────────────────────── 검색 결과 목록 파싱 ──────────────
DEBUG_HTML = False  # True로 바꾸면 첫 검색 결과 HTML을 파일로 저장


def parse_list_page(driver, dump_html=False):
    """현재 페이지의 검색 결과 목록에서 게시글 정보 추출"""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = []

    # 디버그: HTML 구조 확인용 덤프
    if dump_html or DEBUG_HTML:
        with open("_theqoo_debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        log("  [DEBUG] HTML 저장 → _theqoo_debug_page.html")

    # XE/Rhymix 통합검색 결과: .searchResult 또는 ul.searchResult li
    # 게시판 목록형: table.bd_lst tbody tr
    # 더쿠 통합검색 결과: div.search_list 등 다양한 구조 가능

    # ── 패턴 1: 통합검색 결과 (ul/li 구조) ──
    for li in soup.select("ul.searchResult li, div.search_list li, .integrated_result li"):
        a = li.select_one("a[href]")
        if not a:
            continue
        url = a.get("href", "")
        if not url.startswith("http"):
            url = SITE + url
        title = a.get_text(strip=True)
        # 날짜/조회수: li 내부 span 등에서 추출 시도
        date_el = li.select_one(".date, .time, time, .regdate, .side span")
        date_text = date_el.get_text(strip=True) if date_el else ""
        views_el = li.select_one(".count, .views, .readed_count, .side span:last-child")
        views_text = views_el.get_text(strip=True) if views_el else ""
        items.append({
            "url": url, "title": title, "date": date_text,
            "views": views_text, "content": ""
        })

    # ── 패턴 2: 게시판 목록형 (table 구조) ──
    if not items:
        for tr in soup.select("table.bd_lst tbody tr, table.bd_lst_wrp tbody tr"):
            no_td = tr.select_one("td.no")
            if no_td and not no_td.get_text(strip=True).isdigit():
                continue  # 공지 건너뜀

            title_td = tr.select_one("td.title")
            if not title_td:
                continue
            a = title_td.select_one("a[href]")
            if not a:
                continue

            url = a.get("href", "")
            if not url.startswith("http"):
                url = SITE + url
            title = a.get_text(strip=True)

            date_td = tr.select_one("td.time, td.date, td.regdate")
            date_text = date_td.get_text(strip=True) if date_td else ""

            views_td = tr.select_one("td.m_no, td.no_readed, td.readed_count")
            views_text = views_td.get_text(strip=True) if views_td else ""

            items.append({
                "url": url, "title": title, "date": date_text,
                "views": views_text, "content": ""
            })

    # ── 패턴 3: 일반 a 태그 기반 (폴백) ──
    if not items:
        for a in soup.select("a.document_title, a.title_text, .title a[href*='/']"):
            url = a.get("href", "")
            if not url.startswith("http"):
                url = SITE + url
            title = a.get_text(strip=True)
            if title:
                items.append({
                    "url": url, "title": title, "date": "",
                    "views": "", "content": ""
                })

    return items


def has_next_page(driver, current_page):
    """다음 페이지 존재 여부 확인"""
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 페이지네이션 영역에서 다음 페이지 링크 찾기
    paging = soup.select_one(".pagination, .pagenavigation, .paging, .board_pagination")
    if not paging:
        return False

    # 현재 페이지 + 1에 해당하는 링크가 있는지
    next_page = current_page + 1
    for a in paging.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if f"page={next_page}" in href or text == str(next_page):
            return True

    # "다음" 또는 ">" 버튼
    for a in paging.select("a"):
        text = a.get_text(strip=True)
        cls = " ".join(a.get("class", []))
        if text in (">", "다음", "Next") or "next" in cls:
            return True

    return False


# ──────────────────────────── 게시글 본문 수집 ─────────────────
def fetch_post_content(driver, url):
    """개별 게시글에 접속하여 본문, 날짜, 조회수 추출"""
    try:
        driver.get(url)
        delay((1, 2))

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 본문 추출
        content_el = (
            soup.select_one("div.xe_content")
            or soup.select_one("article.xe_content")
            or soup.select_one("div.document_content")
            or soup.select_one("div.rd_body")
            or soup.select_one("#body")
        )
        content = content_el.get_text(separator="\n", strip=True) if content_el else ""

        # 날짜 추출 (목록에서 못 가져온 경우 보충)
        date_el = (
            soup.select_one("span.date, .side span.date, time.date, .read_header span.date")
            or soup.select_one("span.regdate, .time")
        )
        date_text = date_el.get_text(strip=True) if date_el else ""

        # 조회수 추출 (목록에서 못 가져온 경우 보충)
        views_text = ""
        for el in soup.select("span.count, span.readed_count, .side span"):
            txt = el.get_text(strip=True)
            if "조회" in txt or txt.replace(",", "").isdigit():
                views_text = txt.replace("조회", "").replace(" ", "").strip()
                break

        return content, date_text, views_text

    except Exception as e:
        log(f"  본문 수집 실패: {url} ({e})")
        return "", "", ""


# ──────────────────────────── 검색 URL 구성 ───────────────────
def build_search_url(keyword, page=1):
    """더쿠 통합검색 URL 생성 (XE/Rhymix 기반)"""
    params = {
        "act": "IS",
        "is_keyword": keyword,
        "mid": "",
        "page": page,
    }
    return f"{SITE}/index.php?{urlencode(params)}"


# ──────────────────────────── 키워드별 수집 루프 ──────────────
def collect_keyword(driver, keyword):
    """하나의 키워드에 대해 검색 결과 전체를 수집"""
    log(f"=== '{keyword}' 검색 시작 ===")
    all_rows = []
    seen_urls = set()
    page = 1

    while True:
        url = build_search_url(keyword, page)
        log(f"  목록 페이지 {page} 로딩...")
        driver.get(url)
        delay(DELAY_PAGE)

        items = parse_list_page(driver, dump_html=(page == 1))

        # 중복 제거
        new_items = [it for it in items if it["url"] not in seen_urls]
        if not new_items:
            log(f"  페이지 {page}: 새로운 결과 없음 → 목록 수집 종료")
            break

        for it in new_items:
            seen_urls.add(it["url"])
        all_rows.extend(new_items)
        log(f"  페이지 {page}: {len(new_items)}건 추가 (누적 {len(all_rows)}건)")

        if not has_next_page(driver, page):
            log(f"  마지막 페이지 도달 (page={page})")
            break
        page += 1

    log(f"'{keyword}' 목록 수집 완료: 총 {len(all_rows)}건 → 본문 수집 시작")

    # ── 본문 수집 ──
    for i, row in enumerate(all_rows, 1):
        content, date_from_post, views_from_post = fetch_post_content(driver, row["url"])
        row["content"] = content
        if not row["date"] and date_from_post:
            row["date"] = date_from_post
        if not row["views"] and views_from_post:
            row["views"] = views_from_post

        if i % 10 == 0:
            log(f"  본문 수집 중... {i}/{len(all_rows)}")
        delay(DELAY_POST)

        # 중간 저장
        if i % SAVE_EVERY == 0:
            save_excel(all_rows, keyword + "_중간")

    return all_rows


# ──────────────────────────── 메인 ─────────────────────────────
def main():
    driver = create_driver()

    try:
        # 1) 더쿠 접속 + 수동 로그인
        log("더쿠 메인 페이지로 이동합니다...")
        driver.get(SITE)
        print()
        print("=" * 55)
        print("  브라우저에서 더쿠에 로그인해 주세요.")
        print("  로그인 완료 후 여기서 Enter를 누르면 진행됩니다.")
        print("=" * 55)
        input()
        log("로그인 확인 — 검색을 시작합니다.")

        # 2) 검색 키워드 입력
        raw = input("검색 키워드를 콤마(,)로 구분하여 입력: ").strip()
        keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
        if not keywords:
            log("키워드가 입력되지 않았습니다. 종료합니다.")
            return
        log(f"키워드 {len(keywords)}개: {keywords}")

        # 3) 키워드 순차 수집
        for idx, kw in enumerate(keywords, 1):
            rows = []
            try:
                rows = collect_keyword(driver, kw)
                fname = save_excel(rows, kw)
                log(f"[{idx}/{len(keywords)}] '{kw}' 완료 — {len(rows)}건")
            except KeyboardInterrupt:
                log(f"'{kw}' 수집 중 사용자 중단 → 현재까지 저장")
                save_excel(rows, kw + "_중단")
                raise
            except Exception as e:
                log(f"'{kw}' 수집 중 오류: {e}")
                save_excel(rows, kw + "_오류")

            beep()  # 키워드 완료 알림음
            if idx < len(keywords):
                log(f"다음 키워드로 넘어갑니다... (5초 대기)")
                time.sleep(5)

        print()
        log("모든 키워드 수집이 완료되었습니다!")
        beep()

    except KeyboardInterrupt:
        log("사용자에 의해 중단되었습니다.")
    finally:
        driver.quit()
        log("브라우저를 종료했습니다.")


if __name__ == "__main__":
    main()
