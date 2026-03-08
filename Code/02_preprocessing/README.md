# 02_preprocessing — 데이터 전처리

수집된 원본 데이터를 정규화하고, 중복을 제거하여 분석 가능한 형태로 변환하는 스크립트입니다.

## 처리 파이프라인

```
data/1.raw/ (플랫폼별 원본 CSV)
    ↓  merge_sources.py
플랫폼별 병합 CSV
    ↓  normalizer_final.py
표준 형식 정규화 CSV
    ↓  dedupe_validity(중복 제거).py
중복 제거 완료 → data/2.cleaned/
```

## 스크립트 설명

### `merge_sources.py`
플랫폼별로 분산된 소스 CSV 파일을 하나로 병합합니다. 파일명 접두사를 기준으로 플랫폼을 식별하고, URL 기준 중복을 제거합니다.

### `normalizer_final.py`
각 플랫폼마다 상이한 컬럼 구조를 표준 형식으로 정규화합니다.

- **입력 컬럼**: 플랫폼마다 상이 (링크/url/URL, 제목/title, 작성일/date 등)
- **출력 컬럼**: `url`, `사이트`, `작성날짜`, `조회수`, `whole_content`
- 파일 경로와 파일명에서 사이트명을 자동 추출합니다.
- 제목과 본문을 `whole_content` 컬럼으로 결합합니다.

### `dedupe_validity(중복 제거).py`
URL 기준으로 중복 게시물을 제거하고, 사이트별 데이터 통계를 출력합니다.

## 실행 방법

```bash
# 1. 소스 데이터 병합
python merge_sources.py

# 2. 표준 형식 정규화
python normalizer_final.py

# 3. 중복 제거
python "dedupe_validity(중복 제거).py"
```

## 출력

- `data/2.cleaned/cleaned_sample_1. 정제 데이터.csv`
- 표준 컬럼: `url`, `사이트`, `작성날짜`, `whole_content`, `views`
