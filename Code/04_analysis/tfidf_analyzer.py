# -*- coding: utf-8 -*-
"""Validity별 TF-IDF 패턴 비교 분석기"""

import pandas as pd
from pathlib import Path
import os
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


class ValidityTFIDFAnalyzer:
    """Validity 0/1/2 그룹별 TF-IDF 패턴 분석"""

    def __init__(self, cv8_folder: Path):
        self.cv8_folder = cv8_folder
        self.data = {}
        self.tfidf_results = {}

    def load_data(self):
        """V0, V1, V2 파일 로드"""
        files = {
            'V0_invalid': 'validity_0_invalid_no_url.csv',
            'V1_normal': 'validity_1_normal_no_url.csv',
            'V2_strong': 'validity_2_strong_no_url.csv'
        }

        print("Loading validity files...\n")
        for key, filename in files.items():
            filepath = self.cv8_folder / filename
            if not filepath.exists():
                print(f"  [WARN] {filename} not found - skipping")
                continue

            df = pd.read_csv(filepath, encoding='utf-8-sig', low_memory=False)

            # 제목 + 본문 합치기
            if '제목' in df.columns and '본문' in df.columns:
                combined = df['제목'].fillna('').astype(str) + " " + df['본문'].fillna('').astype(str)
            else:
                print(f"  [ERROR] Required columns not found in {filename}")
                continue

            self.data[key] = {
                'df': df,
                'combined_text': combined.tolist(),
                'count': len(df)
            }

            print(f"  [{key}] Loaded: {len(df):,} rows")

        print()

    def analyze_tfidf(self, max_features=100, min_df=5, max_df=0.8):
        """각 그룹별 TF-IDF 분석

        Args:
            max_features: 최대 추출 키워드 수
            min_df: 최소 문서 빈도 (5개 문서 이상에 등장)
            max_df: 최대 문서 빈도 비율 (80% 이하 문서에만 등장)
        """
        print(f"Analyzing TF-IDF (max_features={max_features}, min_df={min_df}, max_df={max_df})...\n")

        for key, data_dict in self.data.items():
            print(f"Processing {key}...")

            # TF-IDF 벡터화 (한글 단어 단위)
            vectorizer = TfidfVectorizer(
                max_features=max_features,
                min_df=min_df,
                max_df=max_df,
                token_pattern=r'[가-힣]+',  # 한글만
                ngram_range=(1, 2)  # 단일 단어 + 바이그램
            )

            try:
                tfidf_matrix = vectorizer.fit_transform(data_dict['combined_text'])
                feature_names = vectorizer.get_feature_names_out()

                # 평균 TF-IDF 점수 계산
                mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

                # 상위 키워드 추출
                top_indices = mean_tfidf.argsort()[::-1]
                top_keywords = [(feature_names[i], mean_tfidf[i]) for i in top_indices]

                self.tfidf_results[key] = {
                    'vectorizer': vectorizer,
                    'keywords': top_keywords,
                    'feature_names': feature_names
                }

                print(f"  Extracted {len(top_keywords)} keywords")

            except Exception as e:
                print(f"  [ERROR] {e}")

        print()

    def print_top_keywords(self, top_n=50):
        """각 그룹의 상위 키워드 출력"""
        print(f"{'='*80}")
        print(f"Top {top_n} Keywords by Validity Group")
        print(f"{'='*80}\n")

        for key in ['V0_invalid', 'V1_normal', 'V2_strong']:
            if key not in self.tfidf_results:
                continue

            keywords = self.tfidf_results[key]['keywords'][:top_n]

            print(f"[{key}] ({self.data[key]['count']:,} rows)")
            print("-" * 80)

            for i, (word, score) in enumerate(keywords, 1):
                print(f"  {i:2d}. {word:20s} (TF-IDF: {score:.4f})")

            print()

    def compare_groups(self, top_n=30):
        """그룹 간 키워드 비교 분석"""
        print(f"{'='*80}")
        print(f"Keyword Comparison Between Groups (Top {top_n})")
        print(f"{'='*80}\n")

        # 각 그룹의 상위 키워드 세트
        v0_set = set([kw for kw, _ in self.tfidf_results.get('V0_invalid', {}).get('keywords', [])[:top_n]])
        v1_set = set([kw for kw, _ in self.tfidf_results.get('V1_normal', {}).get('keywords', [])[:top_n]])
        v2_set = set([kw for kw, _ in self.tfidf_results.get('V2_strong', {}).get('keywords', [])[:top_n]])

        # V0에만 있는 키워드 (invalid 특징)
        v0_only = v0_set - v1_set - v2_set
        print(f"[V0 Only] Invalid-specific keywords ({len(v0_only)}):")
        print(f"  {', '.join(sorted(v0_only)[:20])}")
        print()

        # V1에만 있는 키워드 (normal valid 특징)
        v1_only = v1_set - v0_set - v2_set
        print(f"[V1 Only] Normal-valid-specific keywords ({len(v1_only)}):")
        print(f"  {', '.join(sorted(v1_only)[:20])}")
        print()

        # V2에만 있는 키워드 (strong valid 특징)
        v2_only = v2_set - v0_set - v1_set
        print(f"[V2 Only] Strong-valid-specific keywords ({len(v2_only)}):")
        print(f"  {', '.join(sorted(v2_only)[:20])}")
        print()

        # V1과 V2에 공통 (valid 특징)
        v1_v2_common = v1_set & v2_set - v0_set
        print(f"[V1 & V2 Common] Valid-specific keywords ({len(v1_v2_common)}):")
        print(f"  {', '.join(sorted(v1_v2_common)[:20])}")
        print()

        # 세 그룹 모두 공통 (일반 담론)
        all_common = v0_set & v1_set & v2_set
        print(f"[All Common] General keywords ({len(all_common)}):")
        print(f"  {', '.join(sorted(all_common)[:20])}")
        print()

    def save_results(self, output_folder: Path):
        """결과를 CSV 파일로 저장"""
        output_folder.mkdir(exist_ok=True)

        for key, results in self.tfidf_results.items():
            keywords = results['keywords']

            df = pd.DataFrame(keywords, columns=['keyword', 'tfidf_score'])
            output_path = output_folder / f'tfidf_{key}.csv'
            df.to_csv(output_path, index=False, encoding='utf-8-sig')

            print(f"Saved: {output_path.name}")

        print()


def main():
    """메인 실행 함수"""
    # 최신 cv8 폴더 찾기
    current_folder = Path(os.path.dirname(os.path.abspath(__file__)))
    normalized_folder = current_folder / 'normalized'

    if not normalized_folder.exists():
        print("Error: normalized folder not found")
        return

    cv8_folders = sorted(normalized_folder.glob('cv8_*'))

    if not cv8_folders:
        print("Error: No cv8_* folders found")
        return

    latest_cv8 = cv8_folders[-1]
    print(f"{'='*80}")
    print(f"TF-IDF Validity Pattern Analyzer")
    print(f"Source: {latest_cv8.name}")
    print(f"{'='*80}\n")

    # 분석 실행
    analyzer = ValidityTFIDFAnalyzer(latest_cv8)

    analyzer.load_data()
    analyzer.analyze_tfidf(max_features=100, min_df=10, max_df=0.7)
    analyzer.print_top_keywords(top_n=50)
    analyzer.compare_groups(top_n=30)

    # 결과 저장
    output_folder = latest_cv8 / 'tfidf_analysis'
    print(f"{'='*80}")
    print(f"Saving results...")
    print(f"{'='*80}\n")
    analyzer.save_results(output_folder)

    print(f"{'='*80}")
    print(f"Analysis Complete!")
    print(f"Results saved to: {output_folder}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
