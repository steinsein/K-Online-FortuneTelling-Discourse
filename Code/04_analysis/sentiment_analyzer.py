# -*- coding: utf-8 -*-
"""한국어 감정분석기

All_cleansed_data.csv에 감정분석 결과를 추가합니다.

사용법:
    pip install transformers torch pandas
    python sentiment_analyzer.py
"""

import pandas as pd
import torch
from transformers import pipeline
from pathlib import Path
import os

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = BASE / 'All_cleansed_data.csv'
OUTPUT_DIR = BASE / 'sentiment_results'

# 사용할 모델 (sentiment_test.py로 테스트 후 괜찮은 걸로 변경)
MODEL_NAME = "sangrimlee/bert-base-multilingual-cased-nsmc"

# 배치 크기 (GPU 메모리에 따라 조절, CPU면 작게)
BATCH_SIZE = 128

# 텍스트 최대 길이 (모델 제한)
MAX_LENGTH = 512


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"{'='*70}")
    print("한국어 감정분석기")
    print(f"모델: {MODEL_NAME}")
    print(f"입력: {INPUT_FILE.name}")
    print(f"{'='*70}\n")

    # 1. 데이터 로드
    print("1. 데이터 로드...")
    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig', low_memory=False)
    except:
        df = pd.read_csv(INPUT_FILE, encoding='cp949', low_memory=False)
    print(f"  {len(df)}행 로드 완료")

    # 2. 모델 로드
    print(f"\n2. 모델 로드 중... (처음엔 다운로드 필요)")
    device = 0 if torch.cuda.is_available() else -1
    device_name = "GPU" if device == 0 else "CPU"
    print(f"  디바이스: {device_name}")

    classifier = pipeline(
        "sentiment-analysis",
        model=MODEL_NAME,
        device=device,
        truncation=True,
        max_length=MAX_LENGTH
    )
    print("  모델 로드 완료")

    # 3. 감정분석 수행
    print(f"\n3. 감정분석 수행 중 (배치 크기: {BATCH_SIZE})...")

    texts = df['whole_content'].fillna('').astype(str).tolist()
    total = len(texts)

    labels = []
    scores = []

    for i in range(0, total, BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        # 텍스트 길이 제한
        batch = [t[:MAX_LENGTH] if len(t) > MAX_LENGTH else t for t in batch]

        try:
            results = classifier(batch)
            for r in results:
                labels.append(r['label'])
                scores.append(r['score'])
        except Exception as e:
            # 에러 시 해당 배치는 unknown 처리
            print(f"\n  ! 배치 {i} 에러: {e}")
            for _ in batch:
                labels.append('unknown')
                scores.append(0.0)

        # 진행률
        pct = (i + len(batch)) * 100 // total
        if (i // BATCH_SIZE) % 10 == 0 or i + BATCH_SIZE >= total:
            print(f"\r  [{pct:3d}%] {i + len(batch)}/{total}", end='', flush=True)

    print("\n  완료!")

    # 4. 결과 추가
    df['sentiment_label'] = labels
    df['sentiment_score'] = scores

    # 5. 통계
    print(f"\n4. 결과 통계:")
    counts = df['sentiment_label'].value_counts()
    for label, cnt in counts.items():
        pct = cnt / total * 100
        print(f"  {label}: {cnt}건 ({pct:.1f}%)")

    # 6. 저장
    out_path = OUTPUT_DIR / 'All_cleansed_sentiment.csv'
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n5. 저장 완료: {out_path}")

    # 샘플 출력
    print(f"\n[Positive 샘플]")
    pos = df[df['sentiment_label'].str.contains('positive', case=False, na=False)].head(3)
    for _, row in pos.iterrows():
        snippet = str(row['whole_content'])[:50].replace('\n', ' ')
        print(f"  [{row['sentiment_label']}] {snippet}...")

    print(f"\n[Negative 샘플]")
    neg = df[df['sentiment_label'].str.contains('negative', case=False, na=False)].head(3)
    for _, row in neg.iterrows():
        snippet = str(row['whole_content'])[:50].replace('\n', ' ')
        print(f"  [{row['sentiment_label']}] {snippet}...")

    print(f"\n{'='*70}")
    print("완료!")
    print(f"{'='*70}")

    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 300)
    except:
        print("\a" * 3)


if __name__ == "__main__":
    main()
