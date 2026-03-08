#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 카페 스크래이퍼
사용자 로그인을 통해 회원 전용 카페의 게시글을 검색어 기반으로 스크래이핑합니다.
"""

import time
import os
import pickle
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from config import CAFES


class NaverCafeScraper:
    def __init__(self, headless=False):
        """
        네이버 카페 스크래이퍼 초기화

        Args:
            headless (bool): 브라우저를 숨김 모드로 실행할지 여부
        """
        self.driver = None
        self.wait = None
        self.headless = headless
        self.cookies_file = "naver_cookies.pkl"

    def setup_driver(self):
        """Chrome WebDriver 설정"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        # 일반적인 설정
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User-Agent 설정
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        # 자동화 감지 우회
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def login(self, use_saved_cookies=True):
        """
        네이버 로그인

        Args:
            use_saved_cookies (bool): 저장된 쿠키를 사용할지 여부

        Returns:
            bool: 로그인 성공 여부
        """
        if use_saved_cookies and os.path.exists(self.cookies_file):
            return self._load_cookies()

        return self._manual_login()

    def _load_cookies(self):
        """저장된 쿠키 로드"""
        try:
            self.driver.get("https://naver.com")
            time.sleep(1)

            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                # 쿠키에 expiry가 없거나 만료되지 않은 경우만 추가
                if 'expiry' in cookie:
                    del cookie['expiry']
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"쿠키 추가 실패: {e}")

            # 쿠키 적용 후 페이지 새로고침
            self.driver.refresh()
            time.sleep(2)

            # 로그인 확인
            if self._check_login():
                print("✓ 저장된 쿠키로 로그인 성공")
                return True
            else:
                print("저장된 쿠키가 만료되었습니다. 수동 로그인이 필요합니다.")
                return self._manual_login()

        except Exception as e:
            print(f"쿠키 로드 실패: {e}")
            return self._manual_login()

    def _manual_login(self):
        """수동 로그인 (사용자가 직접 로그인)"""
        print("\n=== 네이버 로그인 ===")
        print("브라우저 창에서 네이버 로그인을 진행해주세요.")
        print("로그인 완료 후 아무 키나 눌러주세요...")

        self.driver.get("https://nid.naver.com/nidlogin.login")

        # 사용자가 로그인할 때까지 대기
        input()

        # 로그인 확인
        if self._check_login():
            print("✓ 로그인 성공!")

            # 쿠키 저장
            self._save_cookies()
            return True
        else:
            print("✗ 로그인 실패. 다시 시도해주세요.")
            return False

    def _check_login(self):
        """로그인 상태 확인"""
        try:
            self.driver.get("https://naver.com")
            time.sleep(1)

            # 로그인 버튼이 없으면 로그인된 상태
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".MyView-module__link_login___HpHMW")
                return False
            except:
                return True
        except:
            return False

    def _save_cookies(self):
        """현재 쿠키 저장"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            print(f"쿠키가 {self.cookies_file}에 저장되었습니다.")
        except Exception as e:
            print(f"쿠키 저장 실패: {e}")

    def scrape_cafe(self, cafe_id, cafe_name, keywords, max_pages=1):
        """
        카페에서 키워드로 게시글 검색 및 스크래이핑

        Args:
            cafe_id (int): 카페 ID (숫자)
            cafe_name (str): 카페 이름 (사용자 표시용)
            keywords (list): 검색 키워드 리스트
            max_pages (int): 각 키워드당 최대 페이지 수

        Returns:
            list: 스크래이핑된 게시글 리스트
        """
        all_posts = []

        print(f"\n[{cafe_name}] 검색 시작...")

        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            print(f"  키워드 '{keyword}' 검색 중 (최대 {max_pages}페이지)...")
            posts = self._search_keyword(cafe_id, cafe_name, keyword, max_pages)
            all_posts.extend(posts)
            print(f"    - 총 {len(posts)}개의 게시글을 찾았습니다.")

            # 네이버 서버 부하 방지를 위한 대기
            time.sleep(2)

        return all_posts

    def _search_keyword(self, cafe_id, cafe_name, keyword, max_pages=0):
        """특정 키워드로 카페 검색 (새로운 네이버 카페 URL 구조 사용)

        Args:
            max_pages: 0이면 끝까지, 양수면 해당 페이지까지
        """
        all_posts = []

        try:
            # URL 인코딩
            encoded_keyword = urllib.parse.quote(keyword)

            # 여러 페이지 스크래이핑
            page = 1
            while True:
                if max_pages > 0:
                    if page > max_pages:
                        break
                    print(f"      페이지 {page}/{max_pages} 처리 중...")
                else:
                    print(f"      페이지 {page} 처리 중...")

                # 새로운 네이버 카페 검색 URL (size=50: 페이지당 50개씩)
                search_url = f"https://cafe.naver.com/f-e/cafes/{cafe_id}/menus/0?viewType=L&ta=ARTICLE_COMMENT&page={page}&q={encoded_keyword}&size=50"

                self.driver.get(search_url)

                # 명시적 대기: 게시글 목록이 로딩될 때까지 기다림
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.article"))
                    )
                    time.sleep(2)  # 추가 안정화 대기
                except Exception as e:
                    print(f"      게시글 로딩 타임아웃 또는 게시글 없음")

                # 페이지 소스 가져오기
                html = self.driver.page_source

                # HTML 디버깅: 첫 페이지의 HTML을 저장
                if page == 1:
                    debug_filename = f"debug_html_{cafe_id}_{keyword}_page{page}.html"
                    with open(debug_filename, 'w', encoding='utf-8') as f:
                        f.write(html)
                    print(f"      [디버그] HTML 저장됨: {debug_filename}")

                soup = BeautifulSoup(html, 'lxml')

                # 네이버 카페 검색 결과 테이블 구조 파싱
                posts = []

                # tr 태그로 게시글 목록 찾기
                article_rows = soup.find_all('tr')

                if not article_rows:
                    print(f"      페이지 {page}: 게시글을 찾을 수 없습니다. HTML 파일을 확인하세요.")
                    break

                for row in article_rows:
                    try:
                        # 제목 링크 추출 (a.article)
                        title_elem = row.select_one('a.article')
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        link = title_elem.get('href', '')

                        # 전체 URL 생성
                        if link and not link.startswith('http'):
                            link = f"https://cafe.naver.com{link}"

                        # 작성자 추출 (span.nickname)
                        author = "알 수 없음"
                        author_elem = row.select_one('span.nickname')
                        if author_elem:
                            author = author_elem.get_text(strip=True)

                        # 작성일 추출 (td.td_normal 중 날짜 형식)
                        date = "알 수 없음"
                        td_normals = row.select('td.td_normal')
                        for td in td_normals:
                            text = td.get_text(strip=True)
                            # 날짜 형식 찾기 (YYYY.MM.DD. 형식)
                            if '.' in text and len(text) >= 10:
                                date = text
                                break

                        # 조회수 추출 (마지막 td.td_normal, 숫자만)
                        views = "0"
                        if td_normals:
                            last_td = td_normals[-1].get_text(strip=True)
                            if last_td.isdigit():
                                views = last_td

                        posts.append({
                            'cafe_name': cafe_name,
                            'keyword': keyword,
                            'title': title,
                            'author': author,
                            'date': date,
                            'views': views,
                            'link': link,
                            'body': ''  # 나중에 채울 예정
                        })

                    except Exception as e:
                        continue

                all_posts.extend(posts)
                print(f"      페이지 {page}: {len(posts)}개 수집")

                # 게시글이 없으면 마지막 페이지 도달
                if len(posts) == 0:
                    print(f"      더 이상 게시글이 없습니다. 총 {page-1}페이지까지 수집 완료.")
                    break

                # 다음 페이지로
                page += 1

                # 다음 페이지로 가기 전 대기
                time.sleep(2)

            # 모든 게시글의 본문 수집
            if all_posts:
                print(f"    총 {len(all_posts)}개 게시글의 본문을 수집합니다...")
                for idx, post in enumerate(all_posts, 1):
                    try:
                        # 10개마다 진행상황 출력
                        if idx % 10 == 0 or idx == 1:
                            print(f"      [{idx}/{len(all_posts)}] 본문 수집 중...")
                        body = self._get_article_body(post['link'])
                        post['body'] = body
                        time.sleep(0.5)  # 서버 부하 방지
                    except Exception as e:
                        print(f"      [{idx}/{len(all_posts)}] 본문 수집 실패: {e}")
                        post['body'] = "[본문 수집 실패]"
                print(f"\n    본문 수집 완료!")

        except Exception as e:
            print(f"    검색 오류: {e}")
            import traceback
            traceback.print_exc()

        return all_posts

    def _get_article_body(self, article_url):
        """게시글 본문 내용 추출"""
        try:
            self.driver.get(article_url)

            # 명시적 대기: 본문 요소가 로딩될 때까지 기다림
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.article_viewer, div.ContentRenderer, div.CafeViewer"))
                )
                time.sleep(0.5)  # 추가 안정화
            except:
                pass  # 타임아웃되어도 계속 진행

            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # 본문 추출 시도 (여러 패턴)
            body_text = ""

            # 패턴 1: 네이버 카페 본문 클래스
            body_elem = soup.select_one('div.article_viewer') or \
                       soup.select_one('div.ContentRenderer') or \
                       soup.select_one('div.CafeViewer') or \
                       soup.select_one('div.article-body') or \
                       soup.select_one('div.se-main-container')

            if body_elem:
                body_text = body_elem.get_text(separator='\n', strip=True)
            else:
                # 패턴 2: iframe 내부 (구 네이버 카페)
                try:
                    self.driver.switch_to.frame("cafe_main")
                    html = self.driver.page_source
                    soup = BeautifulSoup(html, 'lxml')

                    body_elem = soup.select_one('div.article-body') or \
                               soup.select_one('div.se-main-container') or \
                               soup.select_one('div[class*="article"]')

                    if body_elem:
                        body_text = body_elem.get_text(separator='\n', strip=True)

                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()

            # 본문이 비어있으면 기본 메시지
            if not body_text:
                body_text = "[본문을 찾을 수 없음]"

            return body_text

        except Exception as e:
            return f"[오류: {str(e)}]"

    def save_to_excel(self, df, filename=None):
        """결과를 엑셀 파일로 저장"""
        if df.empty:
            print("저장할 데이터가 없습니다.")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"naver_cafe_posts_{timestamp}.xlsx"

        try:
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"\n결과가 {filename}에 저장되었습니다.")
        except Exception as e:
            # openpyxl이 없을 경우 CSV로 저장
            csv_filename = filename.replace('.xlsx', '.csv')
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n결과가 {csv_filename}에 저장되었습니다.")

    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()


def main():
    """메인 함수"""
    print("=" * 60)
    print("네이버 카페 게시글 스크래이퍼")
    print("=" * 60)

    if not CAFES:
        print("\n오류: config.py에 카페가 설정되지 않았습니다.")
        print("config.py 파일을 열어 CAFES 리스트에 카페를 추가해주세요.")
        return

    # 스크래이퍼 실행
    scraper = NaverCafeScraper(headless=False)

    try:
        print("\n브라우저를 시작합니다...")
        scraper.setup_driver()

        # 로그인
        if not scraper.login(use_saved_cookies=True):
            print("로그인에 실패했습니다. 프로그램을 종료합니다.")
            return

        all_results = []

        # 각 카페마다 키워드 입력받기
        for cafe in CAFES:
            cafe_id = cafe['id']
            cafe_name = cafe['name']

            print("\n" + "=" * 60)
            print(f"ID: {cafe_id}를 가지는 카페 \"{cafe_name}\"에 대한 검색을 진행하겠습니다.")
            keywords_input = input("검색어를 입력해 주세요 (콤마 구분): ").strip()

            # 빈 입력이면 건너뛰기
            if not keywords_input:
                print(f"[{cafe_name}] 건너뜁니다.")
                continue

            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

            if not keywords:
                print(f"[{cafe_name}] 유효한 키워드가 없어 건너뜁니다.")
                continue

            # 페이지 수 입력받기
            while True:
                pages_input = input("최대 몇 페이지까지 검색할까요? (0=끝까지, 기본값: 0): ").strip()
                if not pages_input:
                    max_pages = 0  # 0 = 끝까지
                    break
                try:
                    max_pages = int(pages_input)
                    if max_pages < 0:
                        print("0 이상의 숫자를 입력해주세요.")
                        continue
                    break
                except ValueError:
                    print("올바른 숫자를 입력해주세요.")

            # 스크래이핑
            posts = scraper.scrape_cafe(cafe_id, cafe_name, keywords, max_pages)
            all_results.extend(posts)

        # 결과 저장
        if all_results:
            df = pd.DataFrame(all_results)

            # 중복 제거 (제목 + 카페 이름 기준)
            df = df.drop_duplicates(subset=['cafe_name', 'title'], keep='first')

            print("\n" + "=" * 60)
            print(f"총 {len(df)}개의 게시글을 스크래이핑했습니다 (중복 제거 후).")

            scraper.save_to_excel(df)

            # 미리보기 출력
            print("\n=== 결과 미리보기 ===")
            print(df.head(10).to_string())
        else:
            print("\n검색 결과가 없습니다.")

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        print("\n브라우저를 종료합니다.")


if __name__ == "__main__":
    main()
