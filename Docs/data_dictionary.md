# 데이터 사전 (Data Dictionary)

본 문서는 각 데이터 파일의 컬럼 구조와 의미를 설명합니다.

---

## 1. 원본 데이터 (`data/1.raw/`)

플랫폼별로 수집 시점의 원본 구조가 상이합니다.

### `raw_sample_네이버블로그_date.csv`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| title | String | 게시물 제목 |
| link | String | 게시물 URL |
| description | String | 게시물 요약(검색 결과 스니펫) |
| bloggername | String | 블로거 닉네임 |
| bloggerlink | String | 블로그 URL |
| postdate | String | 게시일 (YYYYMMDD) |
| body | String | 게시물 본문 |
| keyword | String | 수집에 사용된 검색 키워드 |

### `raw_sample_dc역학_date.csv`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| url | String | 게시물 URL |
| 사이트 | String | 사이트명 (dc역학) |
| 제목 | String | 게시물 제목 |
| 작성날짜 | String | 게시일 |
| 본문 | String | 게시물 본문 |
| 조회수 | Integer | 조회수 |

### `raw_sample_theqoo_date.csv`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| url | String | 게시물 URL |
| title | String | 게시물 제목 |
| board | String | 게시판 이름 |
| date | String | 게시일 (원본) |
| date_parsed | String | 게시일 (파싱 후) |
| views | Integer | 조회수 |
| content | String | 게시물 본문 |
| keyword | String | 수집에 사용된 검색 키워드 |
| validity | Integer | 유효성 등급 (0/1/2) |

### `raw_sample_네이버카페_date.csv`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| cafe_name | String | 카페 이름 |
| keyword | String | 수집에 사용된 검색 키워드 |
| title | String | 게시물 제목 |
| author | String | 작성자 닉네임 |
| date | String | 게시일 |
| views | Float | 조회수 |
| link | String | 게시물 URL |
| body | String | 게시물 본문 |

### `raw_sample_에펨코리아_date.csv`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| 번호 | Integer | 게시물 번호 |
| 제목 | String | 게시물 제목 |
| 링크 | String | 게시물 URL |
| 글쓴이 | String | 작성자 |
| 작성일 | String | 게시일 |
| 조회 | Integer | 조회수 |
| 본문 | String | 게시물 본문 |

---

## 2. 정제 데이터 (`data/2.cleaned/`)

### `cleaned_sample_1. 정제 데이터.csv`

모든 플랫폼의 데이터를 통합하여 표준 형식으로 정규화한 데이터입니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| url | String | 게시물 URL (고유 식별자) |
| 사이트 | String | 플랫폼명 (네이버블로그, 디시인사이드, 네이버카페, 에펨코리아, 더쿠) |
| 작성날짜 | String | 게시일 (YYYY-MM-DD) |
| whole_content | String | 제목 + 본문 결합 텍스트 |
| views | Float/Integer | 조회수 |

---

## 3. 필터링 데이터 (`data/filtered/`)

### `filtered_sample_2. 정제 데이터(분류적용).csv`

정제 데이터에 규칙 기반 분류 태그를 적용한 데이터입니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| url | String | 게시물 URL |
| 사이트 | String | 플랫폼명 |
| 작성날짜 | String | 게시일 |
| whole_content | String | 제목 + 본문 결합 텍스트 |
| views | Float/Integer | 조회수 |
| is_ad | Boolean | 광고성 콘텐츠 여부 |
| context_type | String | 맥락 유형 (여행/술집/일상/운세집중) |
| channel_type | String | 이용 채널 유형 |
| user_intent | String | 사용자 의도 |

### `filtered_sample_3. 온라인 운세 서비스 후기 데이터.csv`

최종 분석 대상인 운세 서비스 후기 데이터입니다. 컬럼 구조는 `filtered_sample_2`와 동일하며, 광고·여행·일상 맥락 게시물과 오프라인 방문 후기를 제외한 온라인 서비스 후기만 포함합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| url | String | 게시물 URL |
| 사이트 | String | 플랫폼명 |
| 작성날짜 | String | 게시일 |
| whole_content | String | 제목 + 본문 결합 텍스트 |
| views | Float/Integer | 조회수 |
| is_ad | Boolean | 광고성 콘텐츠 여부 |
| context_type | String | 맥락 유형 |
| channel_type | String | 이용 채널 유형 |
| user_intent | String | 사용자 의도 |

---

## 데이터 규모 요약

| 단계 | 파일 | 대략적 건수 |
|------|------|------------|
| 원본 수집 | `data/1.raw/raw_sample_*.csv` | ~700,000건 (전체) |
| 정제 | `data/2.cleaned/cleaned_sample_1.csv` | ~700,000건 |
| 분류 적용 | `data/filtered/filtered_sample_2.csv` | ~700,000건 |
| 최종 후기 | `data/filtered/filtered_sample_3.csv` | ~50,000건 |

> 본 리포지토리에는 용량 제한으로 샘플 데이터만 포함되어 있습니다.
