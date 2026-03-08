# 03_filtering — 데이터 필터링 및 분류

정제된 데이터에서 운세 서비스 후기 게시물을 식별하고, 광고성 콘텐츠를 제거하며, 게시물을 다차원으로 분류하는 스크립트입니다.

## 처리 파이프라인

```
data/2.cleaned/ (정제 데이터, ~700,000건)
    ↓  validator.py
유효성 검증 (V0: 무효 / V1: 일반 / V2: 강한 관련)
    ↓  reviewfinder_3.py
후기 게시물 탐지 (동시출현 조건 기반)
    ↓  filter_reviews.py
분류 태깅 (광고, 맥락, 채널 유형, 사용자 의도)
    ↓  platform_usage_tagger.py
서비스 이용 채널 태깅 (앱/유튜브/AI)
    ↓
data/filtered/ (운세 서비스 후기 데이터, ~50,000건)
```

## 스크립트 설명

### `validator.py`
운세 서비스 담론 유효성 검증기 (v9). 키워드 동시출현(co-occurrence) 규칙을 적용하여 게시물의 관련성 수준을 3단계로 분류합니다.

- **V0 (invalid)**: 운세 서비스와 무관한 게시물
- **V1 (normal)**: 일반적 관련성 (키워드 단독 출현)
- **V2 (strong)**: 강한 관련성 (키워드 동시출현 확인)
- 정밀 필터링: 타로 밀크티, 궁합(음식), 고유명사 등 오탐 방지
- 병렬 처리 지원 (`--part` 인자)

### `reviewfinder_3.py`
동시출현 조건 기반 후기 탐지기 (v3). 골드셋 50건 분석 결과를 반영하여 후기를 3단계로 분류합니다.

- **Strong Review**: 이용행위 키워드 AND (채널/대상 OR 평가) 동시출현
- **Weak Review**: 이용행위 키워드 AND 비용 키워드 동시출현
- **Marginal**: 채널 키워드 AND 평가 키워드 (이용행위 없으나 맥락상 후기)
- TF-IDF + 로지스틱 회귀를 보조적으로 활용

### `filter_reviews.py`
규칙 기반 다중 분류기. 게시물에 다음 태그를 부여합니다.

- `is_ad`: 광고성 콘텐츠 여부 (원고료, 협찬, 체험단 등 키워드 기반)
- `context_type`: 맥락 유형 (여행, 술집, 일상, 운세집중)
- `channel_type`: 이용 채널 유형 (모바일앱, AI/챗봇, 원격/온라인 상담, 전문상담플랫폼, 포털/금융/생활앱, 유튜브/영상, 오프라인/방문 등)
- `user_intent`: 사용자 의도 (직접체험후기, 정보탐색, 자가분석/이론토론 등)

### `platform_usage_tagger.py`
서비스 이용 채널 태거. 다음 불리언 컬럼을 추가합니다.

- `is_app_used`: 운세 앱 이용 여부 (점신, 포스텔러, 만세력 등)
- `is_youtube_used`: 유튜브 운세 콘텐츠 이용 여부
- `is_ai_used`: AI 운세 서비스 이용 여부 (GPT, 뤼튼 등)

## 실행 방법

```bash
# 1. 유효성 검증
python validator.py

# 2. 후기 탐지
python reviewfinder_3.py

# 3. 분류 태깅
python filter_reviews.py

# 4. 채널 태깅
python platform_usage_tagger.py
```

## 출력

- `data/filtered/filtered_sample_2. 정제 데이터(분류적용).csv` — 분류 태그 적용 전체 데이터
- `data/filtered/filtered_sample_3. 온라인 운세 서비스 후기 데이터.csv` — 최종 후기 데이터
- 컬럼: `url`, `사이트`, `작성날짜`, `whole_content`, `views`, `is_ad`, `context_type`, `channel_type`, `user_intent`
