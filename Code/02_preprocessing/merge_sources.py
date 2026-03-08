# -*- coding: utf-8 -*-
"""플랫폼별 소스 데이터 병합기

0_source_data/ 안의 CSV 파일들을 플랫폼별로 병합하고
URL 기준 중복 제거 후 저장합니다.

사용법:
    python merge_sources.py
"""

import pandas as pd
import os
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = BASE / '0_source_data'
OUTPUT_DIR = SOURCE_DIR  # 같은 폴더에 저장

# 플랫폼별 매칭 규칙: (prefix, output_name)
GROUPS = [
    ('dc역학_', 'dc역학_merged.csv'),
    ('theqoo_', 'theqoo_merged.csv'),
    ('디젤매니아,', '네이버카페_merged.csv'),
    ('에펨코리아_', '에펨코리아_merged.csv'),
]


def load_csv(path):
    """CSV 로드 (인코딩 자동 감지)"""
    for enc in ['utf-8-sig', 'cp949', 'euc-kr']:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except (UnicodeDecodeError, Exception):
            continue
    return None


def main():
    print(f"{'='*70}")
    print("플랫폼별 소스 데이터 병합기")
    print(f"소스: {SOURCE_DIR}")
    print(f"{'='*70}\n")

    all_csvs = [f for f in SOURCE_DIR.glob('*.csv') if '_merged' not in f.name]

    for prefix, out_name in GROUPS:
        matched = [f for f in all_csvs if f.name.startswith(prefix)]
        if not matched:
            print(f"[{prefix}*] 파일 없음\n")
            continue

        print(f"[{out_name}] {len(matched)}개 파일")
        print(f"{'-'*50}")

        dfs = []
        total_rows = 0
        for f in sorted(matched):
            df = load_csv(f)
            if df is not None:
                rows = len(df)
                total_rows += rows
                print(f"  {f.name}: {rows}행")
                dfs.append(df)
            else:
                print(f"  {f.name}: 로드 실패!")

        if not dfs:
            print(f"  -> 병합 가능한 파일 없음\n")
            continue

        merged = pd.concat(dfs, ignore_index=True)
        print(f"\n  합계: {total_rows}행")

        # URL 중복 제거
        if 'url' in merged.columns:
            before = len(merged)
            merged.drop_duplicates(subset=['url'], keep='first', inplace=True)
            removed = before - len(merged)
            print(f"  URL 중복 제거: {before} -> {len(merged)}행 (-{removed})")
        elif '링크' in merged.columns:
            before = len(merged)
            merged.drop_duplicates(subset=['링크'], keep='first', inplace=True)
            removed = before - len(merged)
            print(f"  링크 중복 제거: {before} -> {len(merged)}행 (-{removed})")
        else:
            print(f"  ! url/링크 컬럼 없음 — 중복 제거 생략")

        out_path = OUTPUT_DIR / out_name
        merged.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"  -> {out_path.name} ({len(merged)}행 저장)")
        print()

    print(f"{'='*70}")
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
