# -*- coding: utf-8 -*-
"""사용 채널 태거

All_cleansed_data.csv에 is_app_used, is_youtube_used, is_ai_used 컬럼을 추가합니다.

키워드 규칙:
- is_app_used: 점신(+사주/타로/운세/어플 동시출현), 포스텔러, 만세력, 정통사주, 헬로우봇, 운세공감, 더사주, 백점2024
- is_youtube_used: (유튜브/유투브/유튜버) + (사주/타로/운세) 동시출현
- is_ai_used: (gpt/지피티/GPT/ai) + (사주/타로/운세) 동시출현

사용법:
    python usage_tagger.py
"""

import pandas as pd
import re
import os
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = BASE / 'All_cleansed_data.csv'
OUTPUT_DIR = BASE / 'usage_tagged'

# 앱 키워드 (동시출현 불필요)
APP_DIRECT = [
    '포스텔러', '만세력', '정통사주', '헬로우봇', '운세공감', '더사주', '백점2024',
    '카카오운세', '카카오 운세', '오늘의운세', '오늘의 운세',
    '네이버운세', '네이버 운세', '천운', '사주천명', '홍카페',
    '천을귀인', '사주천궁', '사주나루', '신비의거울'
]

# 동시출현 필요 키워드 (일반명사라 오탐 방지)
APP_CONTEXT_REQUIRED = ['점신', '천명', '신통']
APP_CONTEXT = ['사주', '타로', '운세', '어플', '앱']

# 유튜브 키워드 + 동시출현
YOUTUBE_KEYWORDS = ['유튜브', '유투브', '유튜버']
YOUTUBE_CONTEXT = ['사주', '타로', '운세']

# AI 키워드 + 동시출현
AI_KEYWORDS = [
    'gpt', '지피티', '챗지피티', 'chatgpt',
    '클로드', '제미나이', 'gemini', 'ai', '에이아이'
]
AI_CONTEXT = ['사주', '타로', '운세']


def check_app_used(text):
    """앱 사용 여부 체크"""
    if pd.isna(text) or not isinstance(text, str):
        return 'No'

    text_lower = text.lower()

    # 직접 매칭 키워드
    for kw in APP_DIRECT:
        if kw.lower() in text_lower:
            return 'Yes'

    # 동시출현 필요 키워드 (점신, 천명, 신통)
    for kw in APP_CONTEXT_REQUIRED:
        if kw in text:
            for ctx in APP_CONTEXT:
                if ctx in text:
                    return 'Yes'

    return 'No'


def check_youtube_used(text):
    """유튜브 사용 여부 체크"""
    if pd.isna(text) or not isinstance(text, str):
        return 'No'

    # 유튜브 키워드 존재 확인
    has_youtube = any(kw in text for kw in YOUTUBE_KEYWORDS)
    if not has_youtube:
        return 'No'

    # 동시출현 확인
    has_context = any(ctx in text for ctx in YOUTUBE_CONTEXT)
    return 'Yes' if has_context else 'No'


def check_ai_used(text):
    """AI 사용 여부 체크"""
    if pd.isna(text) or not isinstance(text, str):
        return 'No'

    text_lower = text.lower()

    # AI 키워드 존재 확인 (소문자 변환 비교)
    has_ai = any(kw.lower() in text_lower for kw in AI_KEYWORDS)
    if not has_ai:
        return 'No'

    # 동시출현 확인
    has_context = any(ctx in text for ctx in AI_CONTEXT)
    return 'Yes' if has_context else 'No'


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"{'='*70}")
    print("사용 채널 태거")
    print(f"입력: {INPUT_FILE.name}")
    print(f"출력: {OUTPUT_DIR}")
    print(f"{'='*70}\n")

    # 1. 데이터 로드
    print("1. 데이터 로드...")
    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig', low_memory=False)
    except:
        df = pd.read_csv(INPUT_FILE, encoding='cp949', low_memory=False)
    print(f"  {len(df)}행 로드 완료")

    # 2. 태깅 수행
    print("\n2. 태깅 수행 중...")

    text_col = 'whole_content'

    print("  - is_app_used 태깅...", end='', flush=True)
    df['is_app_used'] = df[text_col].apply(check_app_used)
    app_yes = (df['is_app_used'] == 'Yes').sum()
    print(f" {app_yes}건 Yes")

    print("  - is_youtube_used 태깅...", end='', flush=True)
    df['is_youtube_used'] = df[text_col].apply(check_youtube_used)
    youtube_yes = (df['is_youtube_used'] == 'Yes').sum()
    print(f" {youtube_yes}건 Yes")

    print("  - is_ai_used 태깅...", end='', flush=True)
    df['is_ai_used'] = df[text_col].apply(check_ai_used)
    ai_yes = (df['is_ai_used'] == 'Yes').sum()
    print(f" {ai_yes}건 Yes")

    # 3. 결과 통계
    print(f"\n3. 결과 통계:")
    total = len(df)
    print(f"  is_app_used:     Yes {app_yes}건 ({app_yes/total*100:.2f}%) | No {total-app_yes}건")
    print(f"  is_youtube_used: Yes {youtube_yes}건 ({youtube_yes/total*100:.2f}%) | No {total-youtube_yes}건")
    print(f"  is_ai_used:      Yes {ai_yes}건 ({ai_yes/total*100:.2f}%) | No {total-ai_yes}건")

    # 4. 저장
    out_path = OUTPUT_DIR / 'All_cleansed_usage_tagged.csv'
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n4. 저장 완료: {out_path}")

    # 샘플 출력
    print(f"\n[App 사용 샘플 Top 3]")
    app_sample = df[df['is_app_used'] == 'Yes'].head(3)
    for _, row in app_sample.iterrows():
        snippet = str(row[text_col])[:60].replace('\n', ' ')
        print(f"  {snippet}...")

    print(f"\n[YouTube 사용 샘플 Top 3]")
    yt_sample = df[df['is_youtube_used'] == 'Yes'].head(3)
    for _, row in yt_sample.iterrows():
        snippet = str(row[text_col])[:60].replace('\n', ' ')
        print(f"  {snippet}...")

    print(f"\n[AI 사용 샘플 Top 3]")
    ai_sample = df[df['is_ai_used'] == 'Yes'].head(3)
    for _, row in ai_sample.iterrows():
        snippet = str(row[text_col])[:60].replace('\n', ' ')
        print(f"  {snippet}...")

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
