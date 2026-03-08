# -*- coding: utf-8 -*-
"""감성 점수 변환 및 3색 분포 시각화

1. negative 라벨의 점수를 1-score로 변환
2. 변환된 점수 기준으로 재분류:
   - < 0.300: negative
   - > 0.700: positive
   - 0.300 ~ 0.700: neutral
3. 3색 분포 그래프 생성
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

# 한글 폰트 설정 (Windows)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = BASE / 'sentiment_results' / 'All_cleansed_sentiment.csv'
OUTPUT_DIR = BASE / 'sentiment_result_new'


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"{'='*70}")
    print("감성 점수 변환 및 3색 분포 시각화")
    print(f"{'='*70}\n")

    # 1. 데이터 로드
    print("1. 데이터 로드...")
    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig', low_memory=False)
    except:
        df = pd.read_csv(INPUT_FILE, encoding='cp949', low_memory=False)
    print(f"  전체: {len(df):,}행")

    # 2. 원본 분포 확인
    print("\n2. 원본 라벨 분포:")
    print(df['sentiment_label'].value_counts())

    # 3. 점수 변환: negative는 1-score
    print("\n3. 점수 변환 (negative: 1-score)...")
    df['transformed_score'] = df.apply(
        lambda row: 1 - row['sentiment_score']
        if 'negative' in str(row['sentiment_label']).lower()
        else row['sentiment_score'],
        axis=1
    )

    # 변환 후 통계
    print(f"  변환 전 - 평균: {df['sentiment_score'].mean():.4f}, 중앙값: {df['sentiment_score'].median():.4f}")
    print(f"  변환 후 - 평균: {df['transformed_score'].mean():.4f}, 중앙값: {df['transformed_score'].median():.4f}")

    # 4. 새 라벨 부여
    print("\n4. 새 라벨 부여 (0.3 미만=negative, 0.7 초과=positive, 그 외=neutral)...")

    def assign_new_label(score):
        if score < 0.300:
            return 'negative'
        elif score > 0.700:
            return 'positive'
        else:
            return 'neutral'

    df['new_label'] = df['transformed_score'].apply(assign_new_label)

    # 새 라벨 분포
    print("\n  새 라벨 분포:")
    label_counts = df['new_label'].value_counts()
    for label, count in label_counts.items():
        pct = count / len(df) * 100
        print(f"    {label}: {count:,}건 ({pct:.2f}%)")

    # 5. 변환된 데이터 저장
    output_csv = OUTPUT_DIR / '700k_sentiment_transformed.csv'
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n5. 저장: {output_csv.name}")

    # 6. 시각화
    print("\n6. 시각화 생성...")

    # 색상 정의
    colors = {
        'negative': '#F44336',  # 빨강
        'neutral': '#9E9E9E',   # 회색
        'positive': '#4CAF50'   # 녹색
    }

    # 각 라벨별 점수 분리
    scores_neg = df[df['new_label'] == 'negative']['transformed_score'].values
    scores_neu = df[df['new_label'] == 'neutral']['transformed_score'].values
    scores_pos = df[df['new_label'] == 'positive']['transformed_score'].values

    # ========================================
    # 그래프 1: 히스토그램 (3색 분포)
    # ========================================
    fig, ax = plt.subplots(figsize=(11.9, 5.9), facecolor='white')

    bins = np.linspace(0, 1, 51)  # 0.02 간격

    ax.hist(scores_neg, bins=bins, alpha=0.7, color=colors['negative'],
            label=f'Negative (n={len(scores_neg):,})', edgecolor='white')
    ax.hist(scores_neu, bins=bins, alpha=0.7, color=colors['neutral'],
            label=f'Neutral (n={len(scores_neu):,})', edgecolor='white')
    ax.hist(scores_pos, bins=bins, alpha=0.7, color=colors['positive'],
            label=f'Positive (n={len(scores_pos):,})', edgecolor='white')

    # 경계선 표시
    ax.axvline(0.300, color='black', linestyle='--', linewidth=2, alpha=0.7, label='경계 (0.3, 0.7)')
    ax.axvline(0.700, color='black', linestyle='--', linewidth=2, alpha=0.7)

    ax.set_xlabel('Transformed Sentiment Score', fontsize=20)
    ax.set_ylabel('빈도', fontsize=20)
    ax.legend(loc='upper right', fontsize=10, markerscale=1, handlelength=1.5, borderpad=0.6)
    ax.tick_params(labelsize=20)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xlim(0, 1)

    plt.tight_layout()
    hist_path = OUTPUT_DIR / '700k_sentiment_3color_histogram.png'
    plt.savefig(hist_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  -> {hist_path.name}")

    # ========================================
    # 그래프 2: 밀도 그래프 (KDE)
    # ========================================
    fig, ax = plt.subplots(figsize=(11.9, 5.9), facecolor='white')

    # 밀도 곡선
    from scipy import stats

    x_range = np.linspace(0, 1, 500)

    if len(scores_neg) > 1:
        kde_neg = stats.gaussian_kde(scores_neg)
        ax.fill_between(x_range, kde_neg(x_range), alpha=0.5, color=colors['negative'], label='Negative')
        ax.plot(x_range, kde_neg(x_range), color=colors['negative'], linewidth=2)

    if len(scores_neu) > 1:
        kde_neu = stats.gaussian_kde(scores_neu)
        ax.fill_between(x_range, kde_neu(x_range), alpha=0.5, color=colors['neutral'], label='Neutral')
        ax.plot(x_range, kde_neu(x_range), color=colors['neutral'], linewidth=2)

    if len(scores_pos) > 1:
        kde_pos = stats.gaussian_kde(scores_pos)
        ax.fill_between(x_range, kde_pos(x_range), alpha=0.5, color=colors['positive'], label='Positive')
        ax.plot(x_range, kde_pos(x_range), color=colors['positive'], linewidth=2)

    # 경계선
    ax.axvline(0.300, color='black', linestyle='--', linewidth=2, alpha=0.7)
    ax.axvline(0.700, color='black', linestyle='--', linewidth=2, alpha=0.7)

    ax.set_xlabel('Transformed Sentiment Score', fontsize=20)
    ax.set_ylabel('밀도 (Density)', fontsize=20)
    ax.legend(loc='upper right', fontsize=10, markerscale=1, handlelength=1.5, borderpad=0.6)
    ax.tick_params(labelsize=20)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1)

    plt.tight_layout()
    kde_path = OUTPUT_DIR / '700k_sentiment_3color_density.png'
    plt.savefig(kde_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  -> {kde_path.name}")

    # ========================================
    # 그래프 3: 파이 차트
    # ========================================
    fig, ax = plt.subplots(figsize=(11.9, 5.9), facecolor='white')

    sizes = [len(scores_neg), len(scores_neu), len(scores_pos)]
    labels_pie = [
        f'Negative\n{len(scores_neg):,}건\n({len(scores_neg)/len(df)*100:.1f}%)',
        f'Neutral\n{len(scores_neu):,}건\n({len(scores_neu)/len(df)*100:.1f}%)',
        f'Positive\n{len(scores_pos):,}건\n({len(scores_pos)/len(df)*100:.1f}%)'
    ]
    colors_pie = [colors['negative'], colors['neutral'], colors['positive']]

    ax.pie(sizes, labels=labels_pie, colors=colors_pie, autopct='', startangle=90,
           wedgeprops={'edgecolor': 'white', 'linewidth': 2},
           textprops={'fontsize': 24})

    plt.tight_layout()
    pie_path = OUTPUT_DIR / '700k_sentiment_3color_pie.png'
    plt.savefig(pie_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  -> {pie_path.name}")

    # 7. 요약 통계
    print(f"\n{'='*70}")
    print("요약 통계")
    print(f"{'='*70}")

    for label in ['negative', 'neutral', 'positive']:
        scores = df[df['new_label'] == label]['transformed_score']
        if len(scores) > 0:
            print(f"\n[{label.upper()}]")
            print(f"  N: {len(scores):,}")
            print(f"  평균: {scores.mean():.4f}")
            print(f"  표준편차: {scores.std():.4f}")
            print(f"  최소: {scores.min():.4f}")
            print(f"  중앙값: {scores.median():.4f}")
            print(f"  최대: {scores.max():.4f}")

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
