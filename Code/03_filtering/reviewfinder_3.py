# -*- coding: utf-8 -*-
"""Review Finder v3 (Full) - 동시출현 조건 기반

골드셋 50개 분석 결과 반영:
  Strong Review = 이용행위 AND (채널/대상 OR 평가)
  Weak Review   = 이용행위 AND 비용
  Marginal      = 채널 AND 평가 (이용행위 키워드 없지만 맥락상 후기)

입력: 2_validity/ val1+val2 (전체)
출력: reviewfinding/rf3_*.csv

사용법:
    python rf3.py
"""

import pandas as pd
import numpy as np
import re
import os
import queue
from pathlib import Path
from multiprocessing import Process, Queue
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
VALIDITY_DIR = BASE / '2_validity'
OUTPUT_DIR = BASE / 'reviewfinding'
TEXT_MAX_LEN = 5000

# ==========================================
# v3 키워드 정의 (역할별 분리)
# ==========================================

# --- 제외 조건 ---
ai_usage_intent = [
    '프롬프트', '지시문', '명령어', '설정', '오류', '에러',
    '답변 안함', '거부', '유료인가요', '무료인가요', '토큰', 'api',
]

intent_keywords = [
    '추천해', '어디가', '어디서', '잘보는곳', '공유좀', '소개좀', '봐주실', '봐주세요', '봐줘',
    '있나요', '계신가요', '맞나요', '틀린가요', '어때', '어떰', '궁금', '질문',
    '가야하나', '갈까', '믿을만', '할까요', '부탁', '인가요', '건가요',
    '고 싶', '고싶', '가려고', '보려고', '할려고', '볼까', '할까', '해야지',
]

filter_keywords = [
    '황교안', '윤석열', '이재명', '문재인', '박근혜', '노무현', '조국', '한동훈', '박수홍', '현아',
    '장원영', '카리나', '김영하', '이승만', '손흥민', '김민재', '이강인', '류현진',
    '운영자', '관리자', '만든', '제작', '홍보', '바이럴', '광고', '주인', '업자', '알바',
    '노래', '음악', '곡', '앨범', '직캠', '뮤비', '영화', '드라마', '예능', '애니',
    '사줄', '사줘', '사주기', '사줌', '사준', '사고', '사줄게', '밥사주', '술사주', '선물',
    '주식', '증시', '코스피', '부동산', '매매', '전세', '월세', '화짱조', '짱깨'
]

theory_safe_in_review = [
    '도화', '역마', '삼재', '아홉수', '대운', '세운', '용신', '기신', '일주', '사주팔자', '운세', '미신', '부적'
]

theory_keywords_all = [
    '분석', '특징', '공통점', '순위', '차이', '비교', '팩트', '이유', '수기신', '화용신', '교운기',
    '임오월', '을사년', '대운', '세운', '월운', '원국', '명식', '지장간', '무재', '무관', '무인성',
    '재다', '관다', '인다', '재성', '관성', '인성', '비겁', '식상', '편관', '칠살', '정관',
    '천을귀인', '도화', '홍염', '역마', '백호', '괴강', '귀문', '원진', '충', '합', '형',
    '일주', '월주', '시주', '격국', '용신', '기신', '조후', '억부', '신강', '신약', '종격',
    '오행', '목화', '수목', '금수', '토금', '화토', '십성', '육친', '생극제화', '근묘화실'
]

# --- A. 본인 이용 행위 (과거형/경험형) — 리뷰 필수 조건 ---
usage_action_keywords = [
    # 방문/대면
    '보러갔', '보러간', '보러감', '다녀왔', '다녀옴', '찾아갔', '찾아감', '찾아가봤', '찾아가봄',
    '갔다옴', '갔다왔', '갔다온', '보고옴', '보고왔', '보고온',
    # 상담/서비스 수령
    '상담받', '상담했', '상담봤', '풀이받', '통변받', '간명받',
    '봐줬', '봐주신', '봐주시', '봐주던', '해주신', '해주시', '해줬',
    # 직접 이용 (과거형)
    '봤는데', '봤음', '봤었', '봤거든', '봤다', '본적', '봐봤', '봐봄',
    '점봤', '점봄', '점본', '사주봤', '사주봄', '사주본', '신점봤', '신점봄',
    '타로봤', '타로봄', '궁합봤', '궁합봄',
    # 앱/사이트 이용
    '깔았', '다운받', '설치했', '써봤', '써봄', '써본', '해봤', '해봄', '해본',
    '돌려봤', '넣어봤', '결제했', '결제함', '결제해봤',
    # 복합 경험
    '보고다님', '보고다녔', '보러다녔', '보러다님',
    '내돈내산', '발품',
    # 예약/방문
    '예약하고', '예약잡고', '예약해서',
]

# --- B. 채널/장소/대상 특정 ---
channel_keywords = [
    # 오프라인
    '점집', '철학관', '철학원', '신당', '무당집', '타로집', '타로샵', '사주카페', '작명소',
    # 사람/직함
    '술사', '무당', '보살', '역술인', '점쟁이',
    # 온라인 채널
    '카톡타로', '카톡사주', '오픈챗', '옾톡', '전화상담', '060',
    # 어플 (점신 제외 — 점심 오타 문제로 별도 처리)
    '엑스퍼트', '크몽', '탈잉', '포스텔러', '헬로우봇', '천명', '라비', '백점',
    # AI
    '챗GPT', '지피티', 'GPT',
    # 동영상 플랫폼
    '유튜브', 'youtube', 'YouTube', '틱톡', 'tiktok', 'TikTok', '숏츠', 'shorts',
    # 일반
    '어플', '앱',
]

# 점신: 단독 X, 사주/타로 공출현 필수
jeomsin_keyword = ['점신']
jeomsin_context = ['사주', '타로', '운세', '신점', '궁합', '역학', '점술']

# --- C. 결과 평가/정확도 판정 ---
evaluation_keywords = [
    # 긍정
    '잘맞', '잘봄', '잘본', '잘보더', '잘봐', '개잘봄',
    '소름돋', '소름ㄷ', '개소름', '존나소름',
    '용하', '적중', '대만족', '만족했', '만족함',
    '다맞', '다맞히', '다맞추', '딱맞',
    '시원하게', '확실하게',
    # 부정
    '안맞', '못맞', '다틀', '틀림', '틀렸', '틀리더',
    '사기', '엉터리', '돌팔이', '끼워맞추', '끼워맞',
    '못보', '못봄', '못본',
    '실망', '별로', '비추', '돈아까', '돈값안',
    # 혼합/비교
    '반만맞', '반정도', '가끔맞', '맞기도', '맞는것도',
    # 후기 자체 표현
    '후기', '리뷰', '사용후기', '이용후기', '경험담',
    '결론적으로', '총평',
]

# --- D. 비용/거래 ---
cost_keywords = [
    '복비', '점사비', '상담비', '복채', '돈값', '결제', '환불', '입금', '예약금',
    '만원', '만 원', '천원', '무료', '유료', '가격', '비용', '돈주고', '돈 주고',
    '깊티', '기프티',
]


# ==========================================
# Okt 배치 워커
# ==========================================
def sanitize_text(text) -> str:
    if not isinstance(text, str):
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[^\uAC00-\uD7A3\u3131-\u318Ea-zA-Z0-9\s.,!?\-]', ' ', text)
    text = re.sub(r'(.)\1{4,}', r'\1\1\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:TEXT_MAX_LEN]


NUM_OKT_WORKERS = 4  # Okt 병렬 워커 수 (CPU 코어에 맞게 조절)


def _okt_worker(input_q, output_q):
    from konlpy.tag import Okt
    okt = Okt()
    while True:
        try:
            msg = input_q.get(timeout=60)
        except queue.Empty:
            continue
        if msg is None:
            break
        idx, text = msg
        try:
            pos_tagged = okt.pos(text, stem=True)
            words = [word for word, pos in pos_tagged if pos in ('Noun', 'Verb', 'Adjective')]
            output_q.put((idx, words))
        except Exception:
            output_q.put((idx, []))


def parallel_tokenize(texts, num_workers=NUM_OKT_WORKERS):
    """멀티프로세스 Okt로 전체 문서를 병렬 토큰화"""
    input_q = Queue()
    output_q = Queue()

    # 워커 프로세스 시작
    workers = []
    for _ in range(num_workers):
        p = Process(target=_okt_worker, args=(input_q, output_q), daemon=True)
        p.start()
        workers.append(p)

    print(f"  Okt 워커 {num_workers}개 시작")

    # 작업 투입
    total = len(texts)
    for i, text in enumerate(texts):
        clean = sanitize_text(str(text))
        input_q.put((i, clean))

    # 종료 신호
    for _ in range(num_workers):
        input_q.put(None)

    # 결과 수집
    results = [''] * total
    collected = 0
    last_pct = 0

    while collected < total:
        try:
            idx, words = output_q.get(timeout=120)
            results[idx] = ' '.join(words) if words else ''
            collected += 1
            pct = collected * 100 // total
            if pct >= last_pct + 1:
                last_pct = pct
                bar = '#' * (pct // 5) + '-' * (20 - pct // 5)
                print(f"\r  [{bar}] {pct}% ({collected}/{total})", end='', flush=True)
                if pct % 10 == 0:
                    try:
                        import winsound
                        winsound.Beep(800, 200)
                    except:
                        print("\a", end='', flush=True)
        except queue.Empty:
            # 워커가 죽었을 수 있음 — 살아있는 워커 체크
            alive = [w for w in workers if w.is_alive()]
            if not alive:
                print(f"\n  ! 모든 워커 종료됨. {collected}/{total} 처리 완료")
                break

    print()  # 줄바꿈

    # 워커 정리
    for w in workers:
        if w.is_alive():
            w.terminate()
            w.join(timeout=5)

    return results


def safe_contains(series, keywords):
    return series.astype(str).str.contains('|'.join(map(re.escape, keywords)), case=False, na=False)


# ==========================================
# main
# ==========================================
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. 데이터 로드 (전체)
    print("1. 데이터 로드 (전체)...")

    file_paths = [
        ('validity_1_normal.csv', VALIDITY_DIR / 'validity_1_normal.csv'),
        ('validity_2_strong.csv', VALIDITY_DIR / 'validity_2_strong.csv'),
    ]

    df_list = []
    for i, (label, path) in enumerate(file_paths, 1):
        if not path.exists():
            print(f"  파일 없음: {label}")
            continue
        print(f"  [{i}/{len(file_paths)}] {label} 로딩 중...", end='', flush=True)
        try:
            temp_df = pd.read_csv(path, encoding='utf-8-sig', low_memory=False, dtype={'whole_content': str})
        except Exception:
            try:
                temp_df = pd.read_csv(path, encoding='cp949', low_memory=False, dtype={'whole_content': str})
            except:
                print(f" 실패!")
                continue

        print(f" {len(temp_df)}행")
        df_list.append(temp_df)

    if not df_list:
        raise ValueError("데이터를 불러오지 못했습니다.")

    df = pd.concat(df_list, ignore_index=True)
    df['whole_content'] = df['whole_content'].fillna('').astype(str)
    print(f"  전체: {len(df)}행")
    if 'url' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['url'], keep='first').reset_index(drop=True)
        print(f"  1차 URL 중복 제거: {before} -> {len(df)}행 (-{before - len(df)})")
    before = len(df)
    df = df.drop_duplicates(subset=['whole_content'], keep='first').reset_index(drop=True)
    print(f"  2차 본문 중복 제거: {before} -> {len(df)}행 (-{before - len(df)})")

    # 3. v3 마스크 (동시출현 조건)
    print(f"\n3. v3 규칙 기반 라벨링 ({len(df)}건)...")

    print("  마스크 계산 중...", end='', flush=True)
    mask_usage = safe_contains(df['whole_content'], usage_action_keywords)
    print(" 이용행위", end='', flush=True)
    mask_channel_base = safe_contains(df['whole_content'], channel_keywords)
    # 점신: 사주/타로 공출현 시에만 채널로 인정
    mask_jeomsin = safe_contains(df['whole_content'], jeomsin_keyword)
    mask_jeomsin_ctx = safe_contains(df['whole_content'], jeomsin_context)
    mask_jeomsin_valid = mask_jeomsin & mask_jeomsin_ctx
    mask_channel = mask_channel_base | mask_jeomsin_valid
    print(" 채널", end='', flush=True)
    mask_eval = safe_contains(df['whole_content'], evaluation_keywords)
    print(" 평가", end='', flush=True)
    mask_cost = safe_contains(df['whole_content'], cost_keywords)
    print(" 비용", end='', flush=True)

    mask_ai_intent = safe_contains(df['whole_content'], ai_usage_intent)
    mask_intent = safe_contains(df['whole_content'], intent_keywords)
    mask_filter = safe_contains(df['whole_content'], filter_keywords)
    print(" 제외조건", end='', flush=True)
    mask_theory_all = safe_contains(df['whole_content'], theory_keywords_all)
    mask_theory_safe = safe_contains(df['whole_content'], theory_safe_in_review)
    mask_pure_theory = mask_theory_all & (~mask_theory_safe)

    mask_len = df['whole_content'].astype(str).str.len() >= 10
    mask_hashtag = df['whole_content'].astype(str).str.contains('#', na=False)

    mask_exclude = mask_intent | mask_filter | mask_ai_intent | mask_hashtag
    print(" 완료!")

    # Strong: 이용행위 + (채널 OR 평가)
    is_strong_review = (
        mask_usage &
        (mask_channel | mask_eval) &
        ~mask_exclude &
        mask_len
    )

    # Weak: 이용행위 + 비용 (strong에 안 걸린 것)
    is_weak_review = (
        mask_usage &
        mask_cost &
        ~is_strong_review &
        ~mask_exclude &
        mask_len
    )

    # Marginal: 채널 + 평가 (이용행위 없지만 맥락상 후기)
    is_marginal_review = (
        mask_channel &
        mask_eval &
        ~is_strong_review &
        ~is_weak_review &
        ~mask_exclude &
        ~mask_pure_theory &
        mask_len
    )

    df['ml_label'] = 0
    df['sample_weight'] = 1.0

    df.loc[is_strong_review, 'ml_label'] = 1
    df.loc[is_strong_review, 'sample_weight'] = 3.0

    df.loc[is_weak_review, 'ml_label'] = 1
    df.loc[is_weak_review, 'sample_weight'] = 2.0

    df.loc[is_marginal_review, 'ml_label'] = 1
    df.loc[is_marginal_review, 'sample_weight'] = 1.0

    n_s = is_strong_review.sum()
    n_w = is_weak_review.sum()
    n_m = is_marginal_review.sum()
    n_non = len(df) - n_s - n_w - n_m

    print(f"-> Strong Reviews (W=3.0): {n_s}")
    print(f"-> Weak Reviews (W=2.0):   {n_w}")
    print(f"-> Marginal (W=1.0):       {n_m}")
    print(f"-> Non-Reviews:            {n_non}")

    print(f"\n  [마스크 히트 통계]")
    print(f"  이용행위: {mask_usage.sum()}")
    print(f"  채널/대상: {mask_channel.sum()}")
    print(f"  평가: {mask_eval.sum()}")
    print(f"  비용: {mask_cost.sum()}")
    print(f"  제외(의도): {mask_intent.sum()}")
    print(f"  제외(필터): {mask_filter.sum()}")
    print(f"  제외(해시태그): {mask_hashtag.sum()}")
    print(f"  점신(전체): {mask_jeomsin.sum()}, 유효(공출현): {mask_jeomsin_valid.sum()}")
    print(f"  제외(이론): {mask_pure_theory.sum()}")

    # 4. ML 학습
    print("\n4. 머신러닝 모델 학습 시작...")

    total_docs = len(df)
    print(f"  Okt 병렬 토큰화 중 ({total_docs}건, 워커 {NUM_OKT_WORKERS}개)...")
    tokenized_texts = parallel_tokenize(df['whole_content'].tolist())
    df['_tokenized'] = tokenized_texts

    print(f"  TF-IDF 벡터화 중...")
    tfidf = TfidfVectorizer(tokenizer=lambda x: x.split(), max_features=5000, min_df=3)
    X = tfidf.fit_transform(df['_tokenized'])
    y = df['ml_label']
    weights = df['sample_weight']
    df.drop(columns=['_tokenized'], inplace=True)
    print("  TF-IDF 완료")

    model = LogisticRegression(class_weight='balanced', max_iter=1000, C=1.0)
    model.fit(X, y, sample_weight=weights)

    print("-> 모델 학습 완료.")

    # 5. 예측 및 저장
    print("\n5. 전체 데이터 재평가 및 저장...")

    probs = model.predict_proba(X)[:, 1]
    df['review_prob'] = probs

    threshold = 0.65
    df['final_prediction'] = df['review_prob'].apply(lambda x: 'Review' if x >= threshold else 'Non-Review')

    # source_type 태깅
    wc = df['whole_content'].astype(str)
    vid_kw = ['유튜브', 'youtube', 'YouTube', '틱톡', 'tiktok', 'TikTok', '숏츠', 'shorts']
    app_kw = ['포스텔러', '헬로우봇', '천명', '라비', '백점', '어플', '앱']
    ai_kw = ['챗GPT', '지피티', 'GPT', 'gpt', 'chatgpt']

    mask_src_vid = safe_contains(wc, vid_kw)
    mask_src_app = safe_contains(wc, app_kw) | mask_jeomsin_valid
    mask_src_ai = safe_contains(wc, ai_kw)

    # 우선순위: AI > 동영상 > 어플 > 오프라인/기타
    df['source_type'] = '오프라인/기타'
    df.loc[mask_src_app, 'source_type'] = '어플'
    df.loc[mask_src_vid, 'source_type'] = '동영상'
    df.loc[mask_src_ai, 'source_type'] = 'AI'

    final_reviews = df[df['final_prediction'] == 'Review'].sort_values(by='review_prob', ascending=False)
    final_trash = df[df['final_prediction'] == 'Non-Review']

    meta_cols = [c for c in df.columns if c not in ('ml_label', 'sample_weight', 'review_prob', 'final_prediction', 'source_type')]
    output_cols = meta_cols + ['source_type', 'review_prob', 'final_prediction']

    review_path = OUTPUT_DIR / 'rf3_ML_Final_Reviews.csv'
    trash_path = OUTPUT_DIR / 'rf3_ML_Final_NonReviews.csv'

    print("  리뷰 CSV 저장 중...", end='', flush=True)
    final_reviews[output_cols].to_csv(review_path, index=False, encoding='utf-8-sig')
    print(f" {len(final_reviews)}행 완료")
    print("  비후기 CSV 저장 중...", end='', flush=True)
    final_trash[output_cols].to_csv(trash_path, index=False, encoding='utf-8-sig')
    print(f" {len(final_trash)}행 완료")

    print("\n" + "=" * 50)
    print(f"[rf3 FULL] 분석 완료!")
    print(f"전체: {len(df)}행")
    print(f"최종 후기: {review_path.name} ({len(final_reviews)}개)")
    print(f"비후기: {trash_path.name} ({len(final_trash)}개)")
    print(f"출력 폴더: {OUTPUT_DIR}")

    src_counts = final_reviews['source_type'].value_counts()
    print(f"\n[후기 source_type 분포]")
    for st, cnt in src_counts.items():
        print(f"  {st}: {cnt}개")
    print("=" * 50)

    print(f"\n[확실한 후기 Top 10]")
    for _, row in final_reviews[['whole_content', 'review_prob']].head(10).iterrows():
        snippet = row['whole_content'][:80].replace('\n', ' ')
        print(f"  {row['review_prob']:.3f} | {snippet}...")

    ambiguous = df[(df['review_prob'] > 0.4) & (df['review_prob'] < 0.6)]
    if not ambiguous.empty:
        print(f"\n[경계선 (0.4~0.6) - {len(ambiguous)}개]")
        for _, row in ambiguous[['whole_content', 'review_prob']].head(5).iterrows():
            snippet = row['whole_content'][:80].replace('\n', ' ')
            print(f"  {row['review_prob']:.3f} | {snippet}...")

    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 300)
    except:
        print("\a" * 3)


if __name__ == "__main__":
    main()
