# K-Online-FortuneTelling-Discourse

한국 온라인 운세 서비스 담론의 플랫폼별 텍스트 분석  
**A Cultural Analytics Approach to Korean Online Fortune-Telling Service Discourse**

---

## 개요

이 리포지토리는 한국의 주요 온라인 커뮤니티 5개 플랫폼에서 수집한 운세 서비스 관련 게시물을 분석한 학술 연구의 코드와 데이터를 포함합니다. Cultural Analytics 방법론을 적용하여 약 700,000건의 게시물에서 약 50,000건의 사용자 후기 데이터를 추출하고, 플랫폼별 담론 특성과 사용자 경험 패턴을 분석합니다.

### 분석 대상 플랫폼

| 플랫폼 | 특성 |
|--------|------|
| **네이버 블로그** | 개인 블로그 기반 후기 중심, 가장 많은 후기 데이터 보유 |
| **DC인사이드 역학 갤러리** | 역술 전문 커뮤니티, 신뢰성/실력 평가 담론 집중 |
| **네이버 카페** | 관심사 기반 커뮤니티, 커뮤니티 지향적 담론 |
| **에펨코리아** | 종합 커뮤니티, 접근성 중심 사용자 패턴 |
| **더쿠(TheQoo)** | 여초 커뮤니티, 재미/흥미 중심의 소비 패턴 |

### 주요 분석 내용

- 플랫폼별 운세 서비스 후기 게시물의 시계열 추이
- 운세 서비스 유형(모바일앱, AI/챗봇, 원격상담, 전문상담플랫폼 등) 분포 비교
- 다차원 사용자 경험 분석 (신뢰성/실력, 위안/공감, 재미/흥미, 편의/접근성, 가치/혜택)
- 감정 분석(Sentiment Analysis)
- AI 기반 운세 서비스(ChatGPT 등) 관련 담론 동향

## 리포지토리 구조

```
├── 01_collection/        # 플랫폼별 웹 스크래핑 코드
├── 02_preprocessing/     # 데이터 정규화, 중복 제거, 병합
├── 03_filtering/         # 광고 필터링, 후기 분류, 유효성 검증
├── 04_analysis/          # 기술통계, 감정분석, TF-IDF, 플랫폼 비교
├── 05_visualization/     # 시각화 코드 및 생성된 그래프
├── data/                 # 원본·정제·필터링 데이터 (샘플)
└── docs/                 # 변수 설명 및 코딩 체계 문서
```

## 데이터 처리 파이프라인

```
원본 수집 (01_collection)
    ↓
정규화 · 중복 제거 · 병합 (02_preprocessing)
    ↓  약 700,000건
규칙 기반 분류 · 후기 필터링 (03_filtering)
    ↓  약 50,000건 (운세 서비스 후기)
분석 · 시각화 (04_analysis, 05_visualization)
```

## 실행 환경

- Python 3.9+
- 주요 의존 패키지: `requirements.txt` 참조

### 설치

```bash
pip install -r requirements.txt
```

### 실행 순서

1. **수집** (`01_collection/`): 각 플랫폼별 수집 스크립트 실행 (Selenium + BeautifulSoup)
2. **전처리** (`02_preprocessing/`): `merge_sources.py` → `normalizer_final.py` → `dedupe_validity.py`
3. **필터링** (`03_filtering/`): `validator.py` → `reviewfinder_3.py` → `filter_reviews.py`
4. **분석** (`04_analysis/`): 각 분석 스크립트 독립 실행 가능
5. **시각화** (`05_visualization/`): 분석 결과 기반 그래프 생성

> ⚠️ 수집 단계는 각 플랫폼의 이용 약관 및 robots.txt를 준수하여 수행되었습니다. 수집 코드 실행 시 해당 사항을 확인해 주세요.

## 데이터

`data/` 폴더에는 각 처리 단계의 샘플 데이터가 포함되어 있습니다. 전체 데이터셋은 용량 문제로 포함되지 않으며, 재현을 위해서는 수집 단계부터 실행해야 합니다.

| 단계 | 파일 | 설명 |
|------|------|------|
| 원본 | `data/1.raw/raw_sample_*.csv` | 플랫폼별 수집 원본 (샘플) |
| 정제 | `data/2.cleaned/cleaned_sample_1.csv` | 정규화 및 중복 제거 후 데이터 |
| 필터링 | `data/filtered/filtered_sample_2.csv` | 분류 태그 적용 데이터 |
| 필터링 | `data/filtered/filtered_sample_3.csv` | 최종 운세 서비스 후기 데이터 |

## 관련 논문

본 리포지토리의 분석 결과는 다음 논문에서 사용되었습니다:

> 투고논문.pdf (현재 심사중)

## 라이선스

이 프로젝트는 [MIT License](LICENSE)를 따릅니다. 학술 목적으로 활용 시 원 논문을 인용해 주시기 바랍니다.

