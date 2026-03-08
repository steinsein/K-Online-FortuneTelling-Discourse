# 04_analysis — 분석

필터링된 데이터를 대상으로 기술통계, 텍스트 분석, 감정 분석 등을 수행하는 스크립트입니다.

## 스크립트 설명

### `descriptive_statistics.py`
기술통계 생성기. 유효 데이터를 기반으로 시계열 통계를 산출합니다.

- 사이트별 주간/분기별 게시물 수 집계
- 연도별 추이 라인 차트 생성
- 운세 서비스 브랜드/키워드 빈도 분석
- Stacked Area Chart 생성

### `platform_comparison.py`
플랫폼 비교 분석 및 시각화 통합 스크립트. 논문의 주요 그래프 대부분을 생성합니다.

- 플랫폼별 데이터 비율 비교 (도넛 차트)
- 운세 서비스 유형별 분포 비교 (플랫폼×채널 도넛 차트)
- 운세 서비스 브랜드별 언급 분포 (버블 차트)
- 다차원 사용자 경험 분석 히트맵 (신뢰성/실력, 위안/공감, 재미/흥미, 편의/접근성, 가치/혜택)
- AI 운세 서비스 비율 분포

### `sentiment_analyzer.py`
한국어 감정 분석기. 전체 정제 데이터(~700,000건) 대상으로 실행합니다.

- 모델: `sangrimlee/bert-base-multilingual-cased-nsmc` (NSMC 파인튜닝)
- 배치 처리 지원 (GPU/CPU 자동 감지)
- 텍스트 최대 길이: 512 토큰

### `sentiment_analyzer_50k.py`
운세 서비스 후기 데이터(~50,000건) 대상 감정 분석기. `sentiment_analyzer.py`와 동일한 모델을 사용하되, 후기 데이터셋에 특화된 입출력 경로를 갖습니다.

### `temporal_trends.py`
시계열 추이 분석 및 시각화. 분기별 게시물 수 추이를 플랫폼별 · 서비스 유형별로 시각화합니다.

- 플랫폼별 전체 후기 게시물 추이
- 운세 서비스 유형별(모바일앱, AI/챗봇, 원격상담 등) 언급 추이
- AI 키워드 빈도값 시계열 추이

### `tfidf_analyzer.py`
유효성 등급(V0/V1/V2)별 TF-IDF 패턴 비교 분석기. 각 그룹의 특징적 용어를 추출하여 분류 기준의 타당성을 검증합니다.

## 실행 방법

```bash
# 기술통계
python descriptive_statistics.py

# 플랫폼 비교 (주요 시각화 포함)
python platform_comparison.py

# 감정 분석 (GPU 권장)
python sentiment_analyzer.py
python sentiment_analyzer_50k.py

# 시계열 추이
python temporal_trends.py

# TF-IDF 분석
python tfidf_analyzer.py
```

## 의존 패키지

```
pandas, numpy, matplotlib, seaborn, scikit-learn, transformers, torch, scipy
```

## 사용 모델

| 모델 | 용도 | 출처 |
|------|------|------|
| `sangrimlee/bert-base-multilingual-cased-nsmc` | 한국어 감정 분석 (긍정/부정) | HuggingFace |
