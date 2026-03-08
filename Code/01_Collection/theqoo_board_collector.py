"""
더쿠 게시판별 키워드 검색 수집기
- hot / talk / square 게시판
- Selenium 수동 로그인 → 쿠키를 requests로 전달 → 빠른 수집
- 게시판×키워드별 CSV + 전체 병합 CSV
"""

from selenium import webdriver
from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import random
import os
import winsound
from datetime import datetime
from urllib.parse import urlencode

# ──────────────────────────── 설정 ────────────────────────────
SITE = "https://theqoo.net"
BOARDS = {
    "hot":    "핫 게시판",
    "talk":   "일상토크",
    "square": "스퀘어",
}
CUTOFF_DATE = "25.10.01"   # 이 날짜 이후 제거

DELAY_PAGE = (2, 4)
DELAY_POST = (1.5, 3)
SAVE_EVERY = 50
MAX_CHARS  = 30000         # whole_content 이 글자 수 초과 시 제거

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theqoo_source")


# ──────────────────────────── 유틸 ─────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def delay(r):
    time.sleep(random.uniform(*r))


def beep():
    for _ in range(3):
        winsound.Beep(800, 300)
        time.sleep(0.15)


def parse_date(text):
    """'25.07.01' → 그대로 반환. 시간만(HH:MM) → None"""
    text = text.strip()
    parts = text.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return text
    return None


# ──────────────────────────── 브라우저 + 세션 ─────────────────
def create_driver():
    opts = webdriver.ChromeOptions()
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    })
    return driver


def transfer_cookies(driver):
    """Selenium 쿠키 → requests.Session"""
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    })
    for cookie in driver.get_cookies():
        sess.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain", ""))
    return sess


# ──────────────────────────── 검색 URL ────────────────────────
def build_search_url(board, keyword, page=1):
    params = {
        "_filter": "search",
        "act": "",
        "mid": board,
        "category": "",
        "group_srl": "",
        "filter_mode": "",
        "search_target": "title_content",
        "search_keyword": keyword,
        "page": page,
    }
    return f"{SITE}/?{urlencode(params)}"


# ──────────────────────────── 목록 파싱 ──────────────────────
def parse_list_page(sess, url):
    """검색 결과 한 페이지 파싱 → (items, has_next)"""
    resp = sess.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for tr in soup.select("table tbody tr, table.bd_lst tbody tr"):
        no_td = tr.select_one("td.no")
        if not no_td:
            continue
        if not no_td.get_text(strip=True).isdigit():
            continue

        time_td = tr.select_one("td.time")
        raw_date = time_td.get_text(strip=True) if time_td else ""

        title_td = tr.select_one("td.title")
        if not title_td:
            continue
        a = title_td.select_one("a[href]")
        if not a:
            continue
        if a.get("class") and "replyNum" in a.get("class", []):
            a = title_td.find("a", class_=lambda c: c != "replyNum")
        if not a:
            continue

        href = a.get("href", "")
        if not href.startswith("http"):
            href = SITE + href
        title = a.get_text(strip=True)

        views = ""
        m_no = tr.select_one("td.m_no")
        if m_no:
            views = m_no.get_text(strip=True)

        items.append({
            "url": href,
            "title": title,
            "date": parse_date(raw_date) or raw_date,
            "views": views,
            "content": "",
            "whole_content": "",
        })

    # 다음 페이지 존재 여부
    has_next = False
    paging = soup.select_one(".pagination, .pagenavigation, .paging, .board_pagination")
    if paging:
        for a_tag in paging.select("a"):
            txt = a_tag.get_text(strip=True)
            cls = " ".join(a_tag.get("class", []))
            if txt in (">", "다음", "Next") or "next" in cls:
                has_next = True
                break

    return items, has_next


# ──────────────────────────── 본문 수집 ──────────────────────
def fetch_content(sess, url):
    try:
        resp = sess.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        content_el = (
            soup.select_one("div.xe_content")
            or soup.select_one("article.xe_content")
            or soup.select_one("div.document_content")
            or soup.select_one("div.rd_body")
        )
        return content_el.get_text(separator="\n", strip=True) if content_el else ""
    except Exception as e:
        log(f"  본문 실패: {url} ({e})")
        return ""


# ──────────────────────────── 저장 ────────────────────────────
def save_csv(rows, filename):
    if not rows:
        return None
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    log(f"저장: {filename} ({len(rows)}건)")
    return path


# ──────────────────────────── 키워드 × 게시판 수집 ────────────
def collect(sess, board, keyword):
    """한 게시판 + 한 키워드의 전체 검색 결과 수집"""
    log(f"--- [{BOARDS[board]}] '{keyword}' 검색 시작 ---")
    all_rows = []
    seen = set()
    page = 1

    # 1) 목록 수집
    while True:
        url = build_search_url(board, keyword, page)
        log(f"  목록 page {page} ...")
        try:
            items, has_next = parse_list_page(sess, url)
        except Exception as e:
            log(f"  페이지 오류: {e}")
            break

        new = [it for it in items if it["url"] not in seen]
        if not new:
            log(f"  새로운 결과 없음 → 종료")
            break

        for it in new:
            seen.add(it["url"])
        all_rows.extend(new)
        log(f"  +{len(new)}건 (누적 {len(all_rows)}건)")

        if not has_next:
            log(f"  마지막 페이지")
            break
        page += 1
        delay(DELAY_PAGE)

    # 2) 본문 수집
    log(f"  본문 수집: {len(all_rows)}건")
    for i, row in enumerate(all_rows, 1):
        row["content"] = fetch_content(sess, row["url"])
        row["whole_content"] = (row["title"] + "\n" + row["content"]) if row["content"] else row["title"]

        if i % 10 == 0:
            log(f"    {i}/{len(all_rows)}")
        delay(DELAY_POST)

    log(f"  [{BOARDS[board]}] '{keyword}' 완료: {len(all_rows)}건")
    return all_rows


# ──────────────────────────── 날짜 필터 ──────────────────────
def filter_by_date(rows):
    """CUTOFF_DATE 이후 게시글 제거"""
    before = len(rows)
    filtered = []
    for r in rows:
        d = parse_date(r["date"])
        if d and d >= CUTOFF_DATE:
            continue
        filtered.append(r)
    removed = before - len(filtered)
    if removed:
        log(f"날짜 필터: {removed}건 제거 ({CUTOFF_DATE} 이후)")
    return filtered


def filter_by_length(rows):
    """whole_content가 MAX_CHARS 초과인 행 제거"""
    before = len(rows)
    filtered = [r for r in rows if len(r.get("whole_content", "")) <= MAX_CHARS]
    removed = before - len(filtered)
    if removed:
        log(f"글자수 필터: {removed}건 제거 ({MAX_CHARS}자 초과)")
    return filtered


# ──────────────────────────── 메인 ────────────────────────────
def main():
    # 1) 로그인
    driver = create_driver()
    driver.get(SITE)
    print()
    print("=" * 55)
    print("  브라우저에서 더쿠에 로그인해 주세요.")
    print("  로그인 완료 후 여기서 Enter를 누르면 진행됩니다.")
    print("=" * 55)
    input()
    log("로그인 세션 전달 중...")
    sess = transfer_cookies(driver)
    driver.quit()
    log("브라우저 종료 → requests 세션으로 전환 완료")

    # 2) 키워드 입력
    raw = input("검색 키워드를 콤마(,)로 구분하여 입력: ").strip()
    keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
    if not keywords:
        log("키워드 없음. 종료.")
        return

    boards = list(BOARDS.keys())
    log(f"게시판: {[BOARDS[b] for b in boards]}")
    log(f"키워드: {keywords}")
    total_combos = len(boards) * len(keywords)
    log(f"총 {total_combos}개 조합 수집 시작")

    # 3) 게시판 × 키워드 순차 수집
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    all_merged = []
    combo = 0

    for board in boards:
        for kw in keywords:
            combo += 1
            rows = []
            try:
                rows = collect(sess, board, kw)
                rows = filter_by_date(rows)
                rows = filter_by_length(rows)

                # 개별 저장
                fname = f"theqoo_{board}_{kw}_{ts}.csv"
                save_csv(rows, fname)

                # 병합용 — 출처 컬럼 추가
                for r in rows:
                    r["board"] = board
                    r["keyword"] = kw
                all_merged.extend(rows)

            except KeyboardInterrupt:
                log(f"사용자 중단 → 현재까지 저장")
                save_csv(rows, f"theqoo_{board}_{kw}_중단_{ts}.csv")
                raise
            except Exception as e:
                log(f"오류: {e}")
                save_csv(rows, f"theqoo_{board}_{kw}_오류_{ts}.csv")

            log(f"[{combo}/{total_combos}] 완료")
            beep()

            if combo < total_combos:
                time.sleep(3)

    # 4) 병합 저장
    if all_merged:
        save_csv(all_merged, f"theqoo_merged_{ts}.csv")

    print()
    log(f"전체 완료! 총 {len(all_merged)}건")
    beep()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("사용자에 의해 중단되었습니다.")
