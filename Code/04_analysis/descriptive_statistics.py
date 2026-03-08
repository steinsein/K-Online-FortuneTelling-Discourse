# -*- coding: utf-8 -*-
"""Descriptor - 기술통계 생성기

2_validity 폴더의 유효 데이터를 분석하여 시계열 통계 생성

기능:
1. V2 + V1 데이터 통합
2. 사이트별 주간 게시물 수 집계
3. 연도별 라인 차트 생성
4. fortune.word / brand.word 키워드 분석
5. Stacked Area Chart 생성

출력:
    3_description/
        ├── 2019/
        │   ├── 에펨코리아.png
        │   ├── 더쿠.png
        │   └── stacked_area.png
        ├── 2020/
        │   └── ...
        ├── keyword_analysis.csv
        └── weekly_data.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import os
from datetime import datetime
import numpy as np

# 한글 폰트 설정 (Windows)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 하드코딩: 데이터 컷오프 날짜
CUTOFF_DATE = '2025-10-01'


def extract_site_category(site_name: str) -> str:
    """
    사이트명에서 카테고리 추출

    규칙:
    - 네이버카페_XXX → XXX (_뒤)
    - 기타_XXX → 기타 (_앞)
    """
    if not isinstance(site_name, str):
        return '기타'

    if '네이버카페_' in site_name:
        # 네이버카페는 _뒤를 사용
        parts = site_name.split('_', 1)
        return parts[1] if len(parts) > 1 else site_name
    else:
        # 나머지는 _앞을 사용
        parts = site_name.split('_', 1)
        return parts[0]


def load_and_merge_data(validity_folder: Path):
    """V2 + V1 데이터 로드 및 병합"""
    print("Loading data...")

    v2_file = validity_folder / 'validity_2_strong_no_url.csv'
    v1_file = validity_folder / 'validity_1_normal_no_url.csv'

    dfs = []

    if v2_file.exists():
        df_v2 = pd.read_csv(v2_file, encoding='utf-8-sig', low_memory=False)
        print(f"  V2: {len(df_v2)} rows")
        dfs.append(df_v2)

    if v1_file.exists():
        df_v1 = pd.read_csv(v1_file, encoding='utf-8-sig', low_memory=False)
        print(f"  V1: {len(df_v1)} rows")
        dfs.append(df_v1)

    if not dfs:
        print("Error: No data files found")
        return None

    df = pd.concat(dfs, ignore_index=True)
    print(f"  Total: {len(df)} rows")

    # 작성날짜 파싱 (여러 형식 지원)
    def parse_date(date_str):
        """다양한 날짜 형식 파싱"""
        if pd.isna(date_str):
            return pd.NaT

        date_str = str(date_str).strip()

        # 시도할 형식들
        formats = [
            '%Y-%m-%d',      # 2025-01-01
            '%Y.%m.%d',      # 2025.01.01
            '%Y/%m/%d',      # 2025/01/01
            '%Y-%m-%d %H:%M:%S',  # 2025-01-01 12:30:00
        ]

        for fmt in formats:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                continue

        # 형식 지정 안 되면 자동 파싱 시도
        try:
            return pd.to_datetime(date_str)
        except:
            return pd.NaT

    df['작성날짜'] = df['작성날짜'].apply(parse_date)

    # 날짜 파싱 실패한 행 제거
    before = len(df)
    df = df.dropna(subset=['작성날짜'])
    if before > len(df):
        print(f"  Removed {before - len(df)} rows with invalid dates")

    # 컷오프 날짜 이후 데이터 제거
    cutoff = pd.to_datetime(CUTOFF_DATE)
    before = len(df)
    df = df[df['작성날짜'] < cutoff]
    if before > len(df):
        print(f"  Removed {before - len(df)} rows after {CUTOFF_DATE}")

    # 사이트 카테고리 추출
    df['site_category'] = df['사이트'].apply(extract_site_category)

    return df


def create_weekly_aggregation(df: pd.DataFrame):
    """주 단위 집계: '그 주의 월요일 00:00'을 week_start로 사용!"""
    print("\nAggregating weekly data...")

    # 날짜 정규화(혹시 모를 시간 성분 제거)
    dt = pd.to_datetime(df['작성날짜']).dt.tz_localize(None, nonexistent='NaT', ambiguous='NaT')
    dt = dt.dt.floor('D')

    # week_start = 해당 날짜가 속한 주의 '월요일 00:00'
    week_start = dt - pd.to_timedelta(dt.dt.weekday, unit='D')
    week_start = week_start.dt.floor('D')

    df = df.copy()
    df['week'] = week_start

    weekly = df.groupby(['week', 'site_category']).size().reset_index(name='count')

    # 안정성: 정렬 (스택/라인 모두 여기서부터 동일한 시간축)
    weekly = weekly.sort_values(['week', 'site_category']).reset_index(drop=True)

    print(f"  Weeks: {weekly['week'].nunique()}")
    print(f"  Sites: {weekly['site_category'].nunique()}")

    return weekly


def create_yearly_grid(weekly_wide: pd.DataFrame, year: int):
    """
    연도별 그리드 생성: 해당 연도의 '주(월요일 시작)' 전체를 생성하고 0으로 채움!
    """
    if 'week' in weekly_wide.columns:
        data = weekly_wide.set_index('week')
    else:
        data = weekly_wide.copy()

    # 정렬 보장
    data = data.sort_index()

    # 연도 범위
    if year == 2025:
        x_min = pd.Timestamp(f'{year}-01-01')
        x_max = pd.Timestamp(f'{year}-10-01')
    else:
        x_min = pd.Timestamp(f'{year}-01-01')
        x_max = pd.Timestamp(f'{year}-12-31')

    # 해당 연도를 커버하는 "월요일 시작 주" 시퀀스 생성
    # x_min이 월요일이 아니면 그 주의 월요일로 내림
    start = x_min - pd.to_timedelta(x_min.weekday(), unit='D')
    # x_max도 포함되게, 마지막 주의 월요일까지 생성
    end = x_max - pd.to_timedelta(x_max.weekday(), unit='D')

    weeks = pd.date_range(start=start, end=end, freq='W-MON')  # 월요일들

    # reindex해서 없는 주는 0으로 채움
    year_grid = data.reindex(weeks).fillna(0)

    # 진짜로 데이터가 하나도 없으면 None
    if (year_grid.sum(axis=1).sum() == 0):
        return None

    return year_grid


def plot_site_timeline(yearly_grid: pd.DataFrame, site: str, year: int, output_path: Path):
    """사이트별 주간 게시물 수 라인 차트"""

    # yearly_grid에서 해당 사이트 데이터 추출
    if site not in yearly_grid.columns:
        return

    site_series = yearly_grid[site]
    weeks = site_series.index
    counts = site_series.values

    # 모두 0이면 스킵
    if counts.sum() == 0:
        return

    # 그래프 생성
    fig, ax = plt.subplots(figsize=(14, 6))

    # X축 범위 설정 (연도 전체) - 먼저 설정
    if year == 2025:
        x_min = pd.Timestamp(f'{year}-01-01')
        x_max = pd.Timestamp(f'{year}-10-01')
    else:
        x_min = pd.Timestamp(f'{year}-01-01')
        x_max = pd.Timestamp(f'{year}-12-31')

    # 데이터 플롯
    ax.plot(weeks, counts, marker='o', linewidth=2, markersize=4)

    # X축 포맷 (autofmt_xdate 대신 수동 설정)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # X축 범위 재설정 (autofmt_xdate가 없으므로 안전)
    ax.set_xlim(x_min, x_max)

    # 분기 세로선 추가
    for quarter in range(1, 5):
        q_start = pd.Timestamp(f'{year}-{quarter*3-2:02d}-01')
        if x_min <= q_start <= x_max:
            ax.axvline(q_start, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            ax.text(q_start, ax.get_ylim()[1] * 0.95, f'Q{quarter}',
                   ha='center', va='top', fontsize=9, color='gray')

    ax.set_xlabel('주 (Week)', fontsize=12)
    ax.set_ylabel('게시물 수', fontsize=12)
    ax.set_title(f'{site} - {year}년 주간 게시물 수', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_stacked_area(yearly_grid: pd.DataFrame, year: int, output_path: Path):
    """Stacked Area Chart - ax.stackplot 사용(축 처리 안정화)!"""

    if yearly_grid is None or len(yearly_grid) == 0:
        return

    pivot = yearly_grid.sort_index()

    # X축 범위
    if year == 2025:
        x_min = pd.Timestamp(f'{year}-01-01')
        x_max = pd.Timestamp(f'{year}-10-01')
    else:
        x_min = pd.Timestamp(f'{year}-01-01')
        x_max = pd.Timestamp(f'{year}-12-31')

    weeks = pivot.index.to_pydatetime()
    cols = list(pivot.columns)

    fig, ax = plt.subplots(figsize=(14, 8))

    # stackplot (각 컬럼을 시리즈로!)
    ys = [pivot[c].values for c in cols]
    ax.stackplot(weeks, ys, labels=cols, alpha=0.7)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    ax.set_xlim(x_min, x_max)

    # 분기선
    for quarter in range(1, 5):
        q_start = pd.Timestamp(f'{year}-{quarter*3-2:02d}-01')
        if x_min <= q_start <= x_max:
            ax.axvline(q_start, color='black', linestyle='--', alpha=0.5, linewidth=1.5)
            ax.text(q_start, ax.get_ylim()[1] * 0.98, f'Q{quarter}',
                    ha='center', va='top', fontsize=10, fontweight='bold')

    ax.set_xlabel('주 (Week)', fontsize=12)
    ax.set_ylabel('게시물 수 (누적)', fontsize=12)
    ax.set_title(f'{year}년 사이트별 주간 게시물 수 (Stacked)', fontsize=14, fontweight='bold')
    ax.legend(title='사이트', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def analyze_keywords(df: pd.DataFrame, output_path: Path):
    """fortune.word / brand.word 키워드 분석"""
    print("\nAnalyzing keywords...")

    # 모든 키워드 수집
    fortune_words = []
    brand_words = []

    for idx, row in df.iterrows():
        # fortune.word 파싱 (예: "사주:3, 타로:1")
        if pd.notna(row.get('fortune.word', '')):
            for item in str(row['fortune.word']).split(','):
                item = item.strip()
                if ':' in item:
                    word, count = item.split(':')
                    fortune_words.extend([word.strip()] * int(count))

        # brand.word 파싱
        if pd.notna(row.get('brand.word', '')):
            for item in str(row['brand.word']).split(','):
                item = item.strip()
                if ':' in item:
                    word, count = item.split(':')
                    brand_words.extend([word.strip()] * int(count))

    # 빈도 계산
    fortune_freq = pd.Series(fortune_words).value_counts()
    brand_freq = pd.Series(brand_words).value_counts()

    # 데이터프레임 생성
    max_len = max(len(fortune_freq), len(brand_freq))

    result = pd.DataFrame({
        'fortune_word': fortune_freq.index.tolist() + [''] * (max_len - len(fortune_freq)),
        'fortune_count': fortune_freq.values.tolist() + [0] * (max_len - len(fortune_freq)),
        'brand_word': brand_freq.index.tolist() + [''] * (max_len - len(brand_freq)),
        'brand_count': brand_freq.values.tolist() + [0] * (max_len - len(brand_freq))
    })

    result.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  Keyword analysis saved: {output_path.name}")
    print(f"  Fortune words: {len(fortune_freq)}")
    print(f"  Brand words: {len(brand_freq)}")


def main():
    """메인 실행"""
    current_folder = Path(os.path.dirname(os.path.abspath(__file__)))
    validity_folder = current_folder / '2_validity'
    output_folder = current_folder / '3_description'
    output_folder.mkdir(exist_ok=True)

    print(f"\n{'='*70}")
    print("Descriptor - 기술통계 생성기")
    print(f"{'='*70}\n")

    # 1. 데이터 로드
    df = load_and_merge_data(validity_folder)
    if df is None:
        return

    # 2. 주간 집계
    weekly = create_weekly_aggregation(df)

    # wide format으로 변환 (week x site_category)
    weekly_wide = weekly.pivot(index='week', columns='site_category', values='count').fillna(0)
    weekly_wide = weekly_wide.reset_index()  # week을 컬럼으로

    # 원본 데이터 저장 (wide format)
    weekly_csv = output_folder / 'weekly_data.csv'
    weekly_wide.to_csv(weekly_csv, index=False, encoding='utf-8-sig')
    print(f"\n[OK] Weekly data saved: {weekly_csv.name}")

    # 3. 연도별 그래프 생성
    years = sorted(weekly['week'].dt.year.unique())
    sites = sorted(weekly['site_category'].unique())

    print(f"\nGenerating graphs for {len(years)} years, {len(sites)} sites...")

    for year in years:
        year_folder = output_folder / str(year)
        year_folder.mkdir(exist_ok=True)

        print(f"\n  Processing {year}...")

        # 연도별 전체 grid 생성 (week x site_category, 0 채움)
        yearly_grid = create_yearly_grid(weekly_wide, year)

        if yearly_grid is None:
            print(f"    - No data for {year}, skipping")
            continue

        # 디버깅: grid 저장
        grid_csv = year_folder / f'_debug_yearly_grid_{year}.csv'
        yearly_grid.to_csv(grid_csv, encoding='utf-8-sig')
        print(f"    - Debug: yearly_grid saved ({yearly_grid.shape[0]} weeks, {yearly_grid.shape[1]} sites)")

        # 사이트별 라인 차트 (yearly_grid의 모든 사이트)
        for site in yearly_grid.columns:
            output_path = year_folder / f'{year}_{site}.png'
            plot_site_timeline(yearly_grid, site, year, output_path)

        print(f"    - Site charts: {len(yearly_grid.columns)} files")

        # Stacked Area Chart
        stacked_path = year_folder / f'{year}_stacked_area.png'
        plot_stacked_area(yearly_grid, year, stacked_path)
        print(f"    - Stacked area chart: stacked_area.png")

    # 4. 키워드 분석
    keyword_path = output_folder / 'keyword_analysis.csv'
    analyze_keywords(df, keyword_path)

    print(f"\n{'='*70}")
    print("All Processing Complete!")
    print(f"Output folder: {output_folder}")
    print(f"{'='*70}\n")

    # 알림
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 300)
    except:
        print("\a" * 3)

    print("🔔 기술통계 생성 완료!")


if __name__ == "__main__":
    main()
