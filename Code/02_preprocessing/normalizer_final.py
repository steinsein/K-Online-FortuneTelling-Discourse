# -*- coding: utf-8 -*-
"""Data Normalizer (Modified)

모든 수집 데이터를 표준 형식으로 정규화
표준 컬럼: url, 사이트, 제목, 작성날짜, 본문, 조회수
"""

import pandas as pd
import re
from pathlib import Path
import os

class DataNormalizer:
    """데이터 정규화 클래스"""

    def __init__(self):
        # 헤더 매핑 규칙
        self.header_mapping = {
            'url': ['링크', 'url', 'URL', 'link', '주소'],
            '제목': ['제목', 'title', '타이틀', '글제목'],
            '작성날짜': ['date_parsed', '작성일', '작성날짜', 'date', '날짜', '등록일', '게시일'],
            '본문': ['본문', 'content', 'body', '내용', '글내용'],
            '조회수': ['조회수', 'views', 'view_count', 'hits', '뷰', 'view', '조회']
        }

        # 표준 컬럼 순서 (조회수 추가)
        self.standard_columns = ['url', '사이트', '작성날짜', '조회수', 'whole_content']

    def extract_site_name(self, file_path: Path, filename: str) -> str:
        """
        파일 경로와 파일명에서 사이트명 추출

        우선순위:
        1. 더쿠: 파일명 기반
        2. 다음카페_여시: 파일명 기반
        3. 다음카페: 폴더명 기반
        4. 네이버카페: 파일명 기반
        5. 기타 (에펨코리아, 디시인사이드): 파일명 첫 2개 토큰
        """
        filename_lower = filename.lower()
        path_str = str(file_path)

        # 1. 더쿠
        if 'theqoo_unse' in filename_lower:
            return '더쿠_운세'
        elif 'theqoo' in filename_lower:
            return '더쿠'

        # 2. 다음카페 여시 (파일명 기반)
        if filename.startswith('daum_여시_'):
            return '다음카페_여성시대'

        # 3. 다음카페 (폴더명 기반)
        if '다음카페' in path_str:
            if '여성시대' in path_str:
                return '다음카페_여성시대'
            elif '쭉빵카페' in path_str:
                return '다음카페_쭉빵카페'
            else:
                return '다음카페'

        # 4. 네이버카페
        if filename.startswith('디젤매니아'):
            return '네이버카페_디젤매니아'

        # 5. 기타: 파일명 첫 2개 토큰
        tokens = filename.replace('.csv', '').split('_')
        if len(tokens) >= 2:
            return f"{tokens[0]}_{tokens[1]}"
        elif len(tokens) == 1:
            return tokens[0]
        else:
            return '미상'

    def find_matching_column(self, df_columns: list, target_mapping: list) -> str:
        """
        DataFrame 컬럼 중에서 매핑 규칙과 일치하는 컬럼 찾기

        Args:
            df_columns: DataFrame의 실제 컬럼 리스트
            target_mapping: 찾고자 하는 컬럼의 가능한 이름들 (우선순위 순서)

        Returns:
            매칭된 컬럼명 또는 None
        """
        # target_mapping 순서대로 찾기 (우선순위 반영)
        for target_col in target_mapping:
            if target_col in df_columns:
                return target_col
        return None

    def normalize_dataframe(self, df: pd.DataFrame, site_name: str) -> pd.DataFrame:
        """
        DataFrame을 표준 형식으로 정규화

        Args:
            df: 원본 DataFrame
            site_name: 사이트명

        Returns:
            정규화된 DataFrame
        """
        normalized_data = {}

        # 각 표준 컬럼에 대해 매핑
        for std_col, possible_cols in self.header_mapping.items():
            matched_col = self.find_matching_column(df.columns.tolist(), possible_cols)

            if matched_col:
                normalized_data[std_col] = df[matched_col]
            else:
                # 매칭 안 되면 N/A
                normalized_data[std_col] = 'N/A'

        # 더쿠 특수 처리: url에 'theqoo' 있으면 board 컬럼으로 사이트명 생성
        if 'url' in normalized_data and 'board' in df.columns:
            # url 컬럼이 Series인 경우 첫 번째 값 확인
            url_sample = normalized_data['url'].iloc[0] if hasattr(normalized_data['url'], 'iloc') else str(normalized_data['url'])

            if 'theqoo' in str(url_sample).lower():
                # board 컬럼 값으로 사이트명 생성
                board_values = df['board'].fillna('기타').astype(str)
                normalized_data['사이트'] = "더쿠_" + board_values
            else:
                normalized_data['사이트'] = site_name
        else:
            # 사이트 컬럼 추가
            normalized_data['사이트'] = site_name

        # whole_content 생성 (제목 + " " + 본문)
        title = normalized_data.get('제목', pd.Series([''] * len(df)))
        content = normalized_data.get('본문', pd.Series([''] * len(df)))

        if isinstance(title, str):
            title = pd.Series([title] * len(df))
        if isinstance(content, str):
            content = pd.Series([content] * len(df))

        normalized_data['whole_content'] = title.fillna('').astype(str) + " " + content.fillna('').astype(str)

        # 표준 컬럼 순서로 DataFrame 생성 (제목, 본문 제외)
        result_df = pd.DataFrame()
        for col in self.standard_columns:
            if col in normalized_data:
                result_df[col] = normalized_data[col]

        return result_df

    def process_file(self, input_path: Path, output_folder: Path) -> bool:
        """
        단일 CSV 파일 정규화

        Args:
            input_path: 입력 파일 경로
            output_folder: 출력 폴더 경로

        Returns:
            성공 여부
        """
        try:
            # CSV 읽기
            try:
                df = pd.read_csv(input_path, encoding='utf-8-sig', low_memory=False)
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(input_path, encoding='cp949', low_memory=False)
                except:
                    df = pd.read_csv(input_path, encoding='euc-kr', low_memory=False)

            if df.empty:
                print(f"  ⚠ Empty file: {input_path.name}")
                return False

            # 사이트명 추출
            site_name = self.extract_site_name(input_path, input_path.name)

            # 정규화
            normalized_df = self.normalize_dataframe(df, site_name)

            # whole_content 3만 자 초과 행 제거
            if 'whole_content' in normalized_df.columns:
                original_len = len(normalized_df)
                normalized_df = normalized_df[normalized_df['whole_content'].astype(str).str.len() <= 30000]
                removed = original_len - len(normalized_df)
                if removed > 0:
                    print(f"  ⚠ Removed {removed} rows (whole_content > 30000 chars)")

            # 출력 파일명 생성
            output_filename = input_path.stem + '_normalized.csv'
            output_path = output_folder / output_filename

            # 저장
            normalized_df.to_csv(output_path, index=False, encoding='utf-8-sig')

            print(f"  ✓ {input_path.name} → {output_filename} (site: {site_name}, rows: {len(normalized_df)})")
            return True

        except Exception as e:
            print(f"  ✗ Error processing {input_path.name}: {e}")
            return False

    def process_folder(self, folder_path: str):
        """
        폴더 내 모든 CSV 파일 정규화

        Args:
            folder_path: 처리할 폴더 경로 (현재 폴더)
        """
        folder = Path(folder_path)

        if not folder.exists():
            print(f"Error: Folder '{folder_path}' does not exist.")
            return

        # 입력/출력 폴더 설정
        source_folder = folder / '0_source_data'
        output_folder = folder / '1_normalized'
        output_folder.mkdir(exist_ok=True)

        if not source_folder.exists():
            print(f"Error: Source folder '0_source_data' does not exist.")
            return

        print(f"\n{'='*70}")
        print(f"Data Normalizer (Modified) - Starting")
        print(f"Source: {source_folder}")
        print(f"Output: {output_folder}")
        print(f"Standard columns: {self.standard_columns}")
        print(f"{'='*70}\n")

        # 0_source_data 폴더에서 재귀적으로 모든 CSV 파일 찾기
        csv_files = list(source_folder.rglob('*.csv'))

        # _normalized, _verified 파일 제외
        csv_files = [f for f in csv_files
                     if '_normalized' not in f.stem
                     and '_verified' not in f.stem]

        if not csv_files:
            print("No CSV files found.")
            return

        print(f"Found {len(csv_files)} CSV files to process\n")

        # 각 파일 처리
        success_count = 0
        fail_count = 0

        for csv_file in csv_files:
            if self.process_file(csv_file, output_folder):
                success_count += 1
            else:
                fail_count += 1

        # 결과 출력
        print(f"\n{'='*70}")
        print(f"Processing Complete!")
        print(f"  Success: {success_count}")
        print(f"  Failed: {fail_count}")
        print(f"  Total: {len(csv_files)}")
        print(f"\nNormalized files saved to: {output_folder}")
        print(f"{'='*70}\n")


def main():
    """메인 실행 함수"""
    normalizer = DataNormalizer()

    # 현재 스크립트가 있는 폴더
    current_folder = os.path.dirname(os.path.abspath(__file__))

    # 정규화 실행
    normalizer.process_folder(current_folder)

    # 완료 알림
    print("\a" * 3)


if __name__ == "__main__":
    main()
