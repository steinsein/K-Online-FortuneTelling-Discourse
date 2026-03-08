"""
더쿠 운세 게시판 — 기간별 전체 수집
2025.07.01 ~ 2025.09.30 기간의 모든 글 수집
(로그인 불필요, requests 기반)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
import winsound
from datetime import datetime

# ──────────────────────────── 설정 ────────────────────────────
BASE_URL = "https://theqoo.net/unse"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

START_DATE = "25.07.01"   # 수집 시작 (이상)
STOP_DATE  = "25.10.01"   # 이 날짜가 보이면 중단
START_PAGE = 170           # 시작 페이지 (오래된 쪽)
DELAY = (1.5, 3.0)        # 요청 간 딜레이 (초)
SAVE_EVERY = 50            # N건마다 중간 저장

session = requests.Session()
session.headers.update(HEADERS)


# ──────────────────────────── 유틸 ─────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def delay():
    time.sleep(random.uniform(*DELAY))


def beep():
    for _ in range(3):
        winsound.Beep(800, 300)
        time.sleep(0.15)


def parse_date(text):
    """'25.07.01' 형식 → 비교 가능한 문자열로 정규화. 시간만 있는 경우 None."""
    text = text.strip()
    # 'YY.MM.DD' 형식 확인
    parts = text.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return text  # 이미 정규화됨
    return None  # 시간(HH:MM) 등 → 오늘 날짜이므로 범위 밖일 수 있음


def in_range(date_str):
    """날짜가 수집 범위 내인지 확인"""
    if date_str is None:
        return False
    return START_DATE <= date_str < STOP_DATE


def is_stop(date_str):
    """수집 중단 조건: STOP_DATE 이후"""
    if date_str is None:
        return False
    return date_str >= STOP_DATE


# ──────────────────────────── 목록 페이지 파싱 ─────────────────
def parse_list_page(page_num):
    """한 페이지의 게시글 목록을 파싱. (items, should_stop) 반환"""
    url = f"{BASE_URL}?page={page_num}"
    resp = session.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    should_stop = False

    for tr in soup.select("table tbody tr, table.bd_lst tbody tr"):
        # 번호
        no_td = tr.select_one("td.no")
        if not no_td:
            continue
        no_text = no_td.get_text(strip=True)
        if not no_text.isdigit():
            continue  # 공지 건너뜀

        # 날짜
        time_td = tr.select_one("td.time")
        if not time_td:
            continue
        raw_date = time_td.get_text(strip=True)
        date_str = parse_date(raw_date)

        # 범위 밖(너무 오래됨) → 건너뛰되 계속 진행
        if date_str and date_str < START_DATE:
            continue

        # 중단 조건: STOP_DATE 이후 날짜 발견
        if is_stop(date_str):
            should_stop = True
            continue  # 이 글은 수집하지 않되, 같은 페이지의 나머지도 확인

        # 범위 안이면 수집
        if not in_range(date_str):
            continue

        # 제목 + URL
        title_td = tr.select_one("td.title")
        if not title_td:
            continue
        a = title_td.select_one("a[href]")
        if not a:
            continue
        # replyNum 제외
        if a.get("class") and "replyNum" in a.get("class", []):
            a = title_td.find("a", class_=lambda c: c != "replyNum")
        if not a:
            continue

        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://theqoo.net" + href
        title = a.get_text(strip=True)

        # 조회수 (td.m_no 또는 번호 뒤 몇 번째 td)
        views = ""
        m_no = tr.select_one("td.m_no")
        if m_no:
            views = m_no.get_text(strip=True)

        items.append({
            "url": href,
            "title": title,
            "date": date_str or raw_date,
            "views": views,
            "content": "",
            "whole_content": "",
        })

    return items, should_stop


# ──────────────────────────── 본문 수집 ───────────────────────
def fetch_content(url):
    """개별 게시글 본문 텍스트 추출"""
    try:
        resp = session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        content_el = (
            soup.select_one("div.xe_content")
            or soup.select_one("article.xe_content")
            or soup.select_one("div.document_content")
            or soup.select_one("div.rd_body")
        )
        if content_el:
            return content_el.get_text(separator="\n", strip=True)
        return ""
    except Exception as e:
        log(f"  본문 실패: {url} ({e})")
        return ""


# ──────────────────────────── 저장 ────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "theqoo_source")


def save(rows, suffix=""):
    if not rows:
        return
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.DataFrame(rows)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = os.path.join(OUTPUT_DIR, f"theqoo_unse_{START_DATE.replace('.', '')}_{STOP_DATE.replace('.', '')}{suffix}_{ts}.csv")
    df.to_csv(fname, index=False, encoding="utf-8-sig")
    log(f"저장: {fname} ({len(rows)}건)")
    return fname


# ──────────────────────────── 메인 ────────────────────────────
def main():
    log(f"수집 범위: {START_DATE} ~ {STOP_DATE} (미만)")
    log(f"시작 페이지: {START_PAGE} (→ 1 방향으로 감소)")

    all_rows = []
    page = START_PAGE

    # ── 1단계: 목록 수집 ──
    while page >= 1:
        log(f"목록 page {page} ...")
        try:
            items, should_stop = parse_list_page(page)
        except Exception as e:
            log(f"  페이지 {page} 오류: {e} → 건너뜀")
            page -= 1
            delay()
            continue

        if items:
            all_rows.extend(items)
            log(f"  +{len(items)}건 (누적 {len(all_rows)}건)")
        else:
            log(f"  해당 범위 게시글 없음")

        if should_stop:
            log(f"  {STOP_DATE} 날짜 감지 → 목록 수집 종료")
            break

        page -= 1
        delay()

    log(f"목록 수집 완료: 총 {len(all_rows)}건")
    if not all_rows:
        log("수집된 글이 없습니다. 시작 페이지를 조정해 보세요.")
        return

    # ── 2단계: 본문 수집 ──
    log("본문 수집 시작...")
    for i, row in enumerate(all_rows, 1):
        row["content"] = fetch_content(row["url"])
        row["whole_content"] = row["title"] + "\n" + row["content"] if row["content"] else row["title"]

        if i % 10 == 0:
            log(f"  본문 {i}/{len(all_rows)}")
        if i % SAVE_EVERY == 0:
            save(all_rows, "_중간")
        delay()

    # ── 3단계: 최종 저장 ──
    save(all_rows)
    log(f"완료! 총 {len(all_rows)}건 수집")
    beep()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("사용자 중단")
