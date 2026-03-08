# -*- coding: utf-8 -*-
"""dedupe_validity.py - URL 기준 중복 제거 및 사이트별 통계

2_validity 폴더의 validity_2_strong.csv, validity_1_normal.csv에서:
1. URL 기준 중복 제거
2. singular_validity_*.csv 파일 생성
3. 사이트별 개수 통계 출력
"""

import pandas as pd
from pathlib import Path
import os


def extract_site_category(site_name: str) -> str:
    """사이트명에서 주요 카테고리 추출"""
    if not isinstance(site_name, str):
        return '기타'

    site_lower = site_name.lower()

    if 'dc역학' in site_name or 'dc' in site_lower:
        return 'dc역학'
    elif '네이버카페' in site_name or '네이버' in site_name:
        return '네이버카페'
    elif '더쿠' in site_name or 'theqoo' in site_lower:
        return '더쿠'
    elif '에펨코리아' in site_name or '에펨' in site_name or 'fmkorea' in site_lower:
        return '에펨코리아'
    else:
        return '기타'


def process_validity_file(input_path: Path, output_folder: Path, file_type: str):
    """단일 validity 파일 처리"""
    if not input_path.exists():
        print(f"  [SKIP] {input_path.name} not found")
        return None

    print(f"\n{'='*50}")
    print(f"Processing: {input_path.name}")
    print(f"{'='*50}")

    # 파일 읽기
    df = pd.read_csv(input_path, encoding='utf-8-sig', low_memory=False)
    original_count = len(df)
    print(f"  Original rows: {original_count}")

    # URL 기준 중복 제거 (첫 번째 항목 유지)
    if 'url' in df.columns:
        df_deduped = df.drop_duplicates(subset=['url'], keep='first')
        deduped_count = len(df_deduped)
        removed_count = original_count - deduped_count
        print(f"  After dedup: {deduped_count} (removed {removed_count} duplicates)")
    else:
        print("  [WARN] 'url' column not found, skipping dedup")
        df_deduped = df
        deduped_count = original_count

    # 결과 저장
    output_filename = f'singular_{file_type}.csv'
    output_path = output_folder / output_filename
    df_deduped.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  Saved: {output_filename}")

    # 사이트별 통계
    if '사이트' in df_deduped.columns:
        df_deduped['site_category'] = df_deduped['사이트'].apply(extract_site_category)

        site_stats = df_deduped['site_category'].value_counts()

        print(f"\n  Site Statistics ({file_type}):")
        print(f"  {'-'*30}")

        # 주요 카테고리 순서대로
        categories = ['dc역학', '네이버카페', '더쿠', '에펨코리아', '기타']
        for cat in categories:
            count = site_stats.get(cat, 0)
            pct = count / deduped_count * 100 if deduped_count > 0 else 0
            print(f"    {cat}: {count} ({pct:.1f}%)")

        print(f"  {'-'*30}")
        print(f"    Total: {deduped_count}")

        return {
            'file_type': file_type,
            'original': original_count,
            'deduped': deduped_count,
            'removed': original_count - deduped_count,
            **{cat: site_stats.get(cat, 0) for cat in categories}
        }

    return None


def main():
    current_folder = Path(os.path.dirname(os.path.abspath(__file__)))
    validity_folder = current_folder / '2_validity'

    if not validity_folder.exists():
        print(f"Error: 2_validity folder not found")
        return

    print(f"\n{'='*60}")
    print("Dedupe Validity - URL 기준 중복 제거")
    print(f"Source: {validity_folder}")
    print(f"{'='*60}")

    # 처리할 파일들
    files_to_process = [
        ('validity_2_strong.csv', 'validity_2_strong'),
        ('validity_1_normal.csv', 'validity_1_normal'),
    ]

    all_stats = []

    for filename, file_type in files_to_process:
        input_path = validity_folder / filename
        stats = process_validity_file(input_path, validity_folder, file_type)
        if stats:
            all_stats.append(stats)

    # 통계 요약 저장
    if all_stats:
        summary_df = pd.DataFrame(all_stats)
        summary_path = validity_folder / 'singular_summary.csv'
        summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
        print(f"\n[OK] Summary saved: singular_summary.csv")

    print(f"\n{'='*60}")
    print("Processing Complete!")
    print(f"{'='*60}\n")

    # 알림
    try:
        import winsound
        winsound.Beep(1000, 300)
    except:
        print("\a")


if __name__ == "__main__":
    main()
