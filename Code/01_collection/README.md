# 01_collection — 데이터 수집

한국 주요 온라인 커뮤니티 5개 플랫폼에서 운세 서비스 관련 게시물을 수집하는 스크립트입니다.

## 수집 대상 및 기간

| 플랫폼 | 수집 기간 | 수집 방식 | 스크립트 |
|--------|-----------|-----------|----------|
| 네이버 블로그 | 2019.01 – 2025.03 | Naver Search API + Selenium | `blog_collector.py` |
| DC인사이드 역학 갤러리 | 2019.01 – 2025.03 | Selenium + BeautifulSoup | `dcgallery_collector.py` |
| 네이버 카페 | 2019.01 – 2025.03 | Naver Cafe API + Selenium | `naver_cafe_collector.py` |
| 에펨코리아 | 2019.01 – 2025.03 | Selenium + BeautifulSoup | `fmkorea_collector.py` |
| 더쿠(TheQoo) | 2019.01 – 2025.03 | Selenium + BeautifulSoup | `theqoo_collector.py` |

## 검색 키워드

운세 서비스 관련 주요 키워드(사주, 타로, 운세, 신점, 작명, 점집, 역술, 포스텔러, 점신, 사주나루 등)를 조합하여 검색하였습니다.

## 스크립트 설명

| 파일 | 설명 |
|------|------|
| `blog_collector.py` | 네이버 블로그 게시물 수집. 월별 날짜 범위 분할 및 병렬 처리 지원 |
| `dcgallery_collector.py` | DC인사이드 역학 갤러리 게시물 수집 |
| `fmkorea_collector.py` | 에펨코리아 게시물 수집 |
| `theqoo_collector.py` | 더쿠 일반 게시물 수집 |
| `theqoo_board_collector.py` | 더쿠 특정 게시판(운세 게시판 등) 대상 수집 |
| `theqoo_unse_period.py` | 더쿠 운세 관련 게시물 기간별 수집 |
| `naver_cafe_collector.py` | 네이버 카페 게시물 수집 |
| `naver_cafe_config.py` | 네이버 카페 수집 대상 목록 설정 파일 |

## 실행 방법

```bash
# 예시: 네이버 블로그 수집
python blog_collector.py

# 예시: DC인사이드 수집
python dcgallery_collector.py
```

## 의존 패키지

```
selenium, webdriver-manager, beautifulsoup4, requests, pandas, python-dateutil, tqdm
```

## 출력

각 스크립트는 `data/1.raw/` 디렉토리에 플랫폼별 CSV 파일을 생성합니다.

## 주의사항

- 각 플랫폼의 이용약관 및 `robots.txt`를 준수하여 수집하였습니다.
- Selenium 실행을 위해 ChromeDriver가 필요합니다 (`webdriver-manager`로 자동 관리).
- 네이버 카페 수집 시 별도의 인증 설정이 필요할 수 있습니다 (`naver_cafe_config.py` 참조).
- 수집 시 서버 부하 방지를 위해 적절한 딜레이가 설정되어 있습니다.
