# -*- coding: utf-8 -*-
"""chiefvalidator_v9

개선사항 (v8 → v9):
1. 병렬 처리 지원:
   - --part 1 또는 --part 2 인자로 파일 분할 처리
   - 2_validity_part1/ 또는 2_validity_part2/ 폴더에 저장
   - merge_validity.py로 나중에 통합

2. 알림 기능 개선:
   - 처리 완료 시 비프음 3회

v8 기능 유지:
- 정밀 필터링 (타로 밀크티, 사주다, 궁합, 고유명사, 스팸)
- validation_summary.csv 생성
"""

import pandas as pd
import re
from typing import Dict, Tuple
from pathlib import Path
import os
import sys
from datetime import datetime


class ReligiousServiceValidator:
    """종교 서비스 담론 유효성 검증기 V9 - 정밀 필터링 + 추적"""

    def __init__(self):
        # === V7 기존 설정 ===
        self.brand_keywords = [
            '포스텔러', '만세력', '점신', '홍카페', '천을귀인',
            '천명', '사주천궁', '신통', '사주나루', '신비의거울', '헬로우봇'
        ]

        self.fortune_keywords = [
            '사주', '타로', '운세', '신점', '작명',  # 궁합 제거 (별도 co-occ 처리)
            '점집', '무당', '역술', '연애운', '애정운', '재물운', '건강운'
        ]

        self.saju_brands = [
            '천을귀인', '포스텔러', '만세력', '점신', '홍카페',
            '천명', '사주천궁', '신통', '사주나루', '신비의거울', '헬로우봇'
        ]
        self.saju_compounds = ['사주팔자', '사주타로', '사주카페']

        # === Co-occurrence 키워드들 (메인 키워드와 함께 나오면 V2) ===

        # 사주 co-occ (기존 + 명리 용어)
        self.saju_cooccur_words = [
            # 기존
            '타로', '운세', '작명', '신점', '궁합', '점집', '무당', '역술',
            '연애운', '애정운', '재물운', '건강운',
            # 명리 용어 추가
            '명리', '명리학', '대운', '세운', '월운', '일운',
            '시주', '일주', '월주', '연주',
            '오행', '십신', '용신', '격국', '신강', '신약',
            '식상', '관성', '재성', '인성', '비겁',
        ]

        # 타로 co-occ
        self.taro_cooccur_words = [
            '카드리딩', '카드 리딩', '스프레드',
            '역방향', '정방향', '역위', '정위',
            '메이저', '마이너', '아르카나',
        ]

        # 신점 co-occ
        self.sinjeom_cooccur_words = [
            '보살', '신내림', '내림굿', '부적', '신당', '무속', '점사',
            '굿', '치성', '기도',
        ]

        # 작명 co-occ
        self.jakming_cooccur_words = [
            '개명', '이름풀이', '성명학', '관상', '손금',
        ]

        # 궁합 유효 키워드 (이것들과 함께 나와야 궁합이 V2)
        self.gunghap_valid_cooccur = [
            '사주', '타로', '운세', '신점', '점집', '무당', '역술',
            '연애운', '애정운', '만세력', '포스텔러',
        ]

        # 운세 co-occ (시간표현 + 서비스)
        self.unse_cooccur_words = [
            # 시간 표현
            '오늘', '이번주', '이번달', '월간', '내일', '모레',
            '새해', '신년', '내년', '올해',
            '상반기', '하반기', '분기', '계절', '월별',
            # 서비스 관련
            '정확', '후기', '리뷰', '결제', '구독',
        ]

        # 운세 V0 필터 (지명 오염)
        self.unse_exclusion_pattern = r'운세구'

        self.saju_postposition_pattern = r'사주[가를의과와에](?![가-힣])'
        self.saju_attachment_pattern = r'사주(?:보러|봤|보고|보니)(?![가-힣])'
        self.saju_exclusion_pattern = r'사주(?:고|거나|지|면|세요|십시오|ㄴ지|ㄹ게|장님|장)'

        self.saju_blacklist = ['자사주', '자기사주']

        self.taro_exclusion_pattern = r'(?:좌|우|지|대|시|인스|쇼|파스|라우|메)타로'

        self.taro_valid_patterns = [
            r'사주타로',
            r'(?<![가-힣])타로[가를의와에도는]',
            r'\s타로\s',
            r'^타로[가를의와에도는]',
        ]

        # === 강한 패턴들 (등장 시 무조건 validity=2) ===

        # 타로 강한 패턴
        self.taro_strong_patterns = [
            r'타로러',
            r'셀프타로',
            r'타로봐',
            r'타로카드',
            r'유튜브\s?타로',
            r'타로\s?리딩',
            r'타로\s?상담',
            r'타로\s?점(?![가-힣])',  # 타로점, 타로 점 (but not 타로점집)
        ]

        # 사주 강한 패턴
        self.saju_strong_patterns = [
            r'사주명리',
            r'사주해석',
            r'사주풀이',
            r'사주상담',
            r'사주\s?앱',
            r'사주\s?어플',
        ]

        # 운세 강한 패턴
        self.unse_strong_patterns = [
            r'네이버\s?운세',
            r'다음\s?운세',
            r'오늘의?\s?운세',
            r'무료\s?운세',
            r'별자리\s?운세',
            r'신년\s?운세',
            r'띠별\s?운세',
            r'인터넷\s?운세',
            r'점성술',
        ]

        # === AI + 사주/타로 패턴 (ai_fortune) ===
        self.ai_tokens = ['gpt', 'GPT', '지피티', '챗지피티', 'chatgpt', 'ChatGPT', 'ai', 'AI', '에이아이']

        # ai_fortune 강한 패턴: GPT사주, AI타로, GPT로 사주, 지피티한테 타로 등
        self.ai_fortune_patterns = [
            # 붙여쓰기: gpt사주, ai타로
            r'(?:gpt|GPT|지피티|챗지피티|chatgpt|ChatGPT|ai|AI|에이아이)\s?(?:사주|타로)',
            # 조사 포함: gpt로 사주, ai한테 타로 (0~2자 허용)
            r'(?:gpt|GPT|지피티|챗지피티|chatgpt|ChatGPT|ai|AI|에이아이)(?:로|한테|에게|로부터)?\s{0,2}(?:사주|타로)',
        ]

        # 신점 강한 패턴
        self.sinjeom_strong_patterns = [
            r'신점\s?봤',
            r'신점\s?보러',
            r'신점\s?본(?![가-힣])',
        ]

        # 작명 강한 패턴
        self.jakming_strong_patterns = [
            r'작명소',
            r'작명원',
        ]

        # 모든 강한 패턴 통합 (validate_text에서 사용)
        self.all_strong_patterns = (
            self.taro_strong_patterns +
            self.saju_strong_patterns +
            self.unse_strong_patterns +
            self.sinjeom_strong_patterns +
            self.jakming_strong_patterns +
            self.ai_fortune_patterns
        )

        self.regular_keywords = {
            "만세력", "신점", "운세", "타로",
            "포스텔러", "점신", "천을귀인"
        }

        self.target_keywords = self.regular_keywords | {"사주"}

        self.strict_cooccurrence = {
            "타로": ["사주", "신점", "궁합", "만세력", "운세", "포스텔러", "점신", "천을귀인", "무당", "점집", "보살"],
            "궁합": ["사주", "타로", "운세", "신점", "만세력", "포스텔러", "점신", "천을귀인", "무당", "점집", "보살", "역술"]
        }

        self.relationship_keywords = [
            "남자친구", "여자친구", "남친", "여친", "연애운", "애정운", "연인", "애인", "연애"
        ]

        self.special_combinations = {
            "엑스퍼트": ["사주", "타로", "운세", "신점"],
            "GPT": ["사주", "타로", "운세"],
            "지피티": ["사주", "타로", "운세"]
        }

        self.whitelist_core = {
            "궁합", "만세력", "사주", "신점", "운세", "타로",
            "무당", "점집", "보살", "역술인"
        }

        self.whitelist_related = {
            "후기", "앱", "어플", "썰",
            "보다", "봤", "볼까", "보는", "본",
            "상담", "해석", "풀이", "리딩",
            "카드", "생년월일", "띠", "신수"
        }

        self.all_whitelist = self.whitelist_core | self.whitelist_related

        # === V8 새로운 필터 패턴 ===

        # ① 식음료 타로 필터
        self.taro_beverage_pattern = r'타로\s*(밀크티|버블티|라떼|쉐이크|맛|파우더|티|공차|팔공티|차타임|아마스빈|당도|펄|토란)'

        # ② 사주다(buy) 필터
        self.buy_context_pattern = r'(밥|술|커피|음식|선물|용돈|옷|가방|뭐)\s*사주'
        self.buy_honorific_pattern = r'사주(신|실|셨|셔서|심|시는|러|려고|려던|려다가|준대|주네)'

        # ③ 비운세형 궁합 필터
        self.gonghap_nonfortune_pattern = r'(얼굴|덩치|피지컬|비주얼|키|나이|목소리|착장|코디|인테리어|가구|부품|렌즈)\s*(궁합|합)'
        self.gonghap_food_pattern = r'(음식|영양제|조합|케미|라면|안주)\s*궁합'

        # ④ 고유명사 필터 (경제/사회/법률/군사)
        self.proper_noun_patterns = [
            r'우리사주', r'주식\s*사주', r'증권\s*사주', r'상장\s*사주',
            r'고발\s*사주', r'청부\s*사주', r'살인\s*사주', r'교사\s*사주', r'배후\s*사주',
            r'사주\s*경계'
        ]

        # ⑤ 스팸 및 도배 패턴
        self.spam_patterns = [
            r'저승사자', r'휴ㅅ휴',
            r'[♡]{2,}',
            r'[!]{3,}',
            r'[?]{3,}'
        ]

    def check_filters(self, text: str) -> Tuple[bool, str]:
        """
        모든 필터 체크 (우선순위 순서대로)

        Returns:
            (should_filter, filter_reason)
            should_filter: True면 제거, False면 통과
            filter_reason: 필터 이유
        """
        if not isinstance(text, str):
            return True, 'invalid_text'

        # ① 1순위: 고유명사 완전 일치
        for pattern in self.proper_noun_patterns:
            if re.search(pattern, text):
                return True, f'proper_noun:{pattern}'

        # ② 2순위: 스팸 패턴
        for pattern in self.spam_patterns:
            if re.search(pattern, text):
                return True, f'spam:{pattern}'

        # ③ 2순위: 타로 음료 필터
        if re.search(self.taro_beverage_pattern, text):
            return True, 'taro_beverage'

        # ④ 3순위: 사주다(buy) 필터
        if re.search(self.buy_context_pattern, text):
            return True, 'buy_context'

        if re.search(self.buy_honorific_pattern, text):
            # 예외: "사주 신뢰도", "사주 실력" 등은 보존
            # 공백이 있으면 명사일 가능성
            if not re.search(r'사주\s+(신|실)', text):
                return True, 'buy_honorific'

        # ⑤ 3순위: 비운세형 궁합 필터
        if re.search(self.gonghap_nonfortune_pattern, text):
            return True, 'gonghap_nonfortune'

        if re.search(self.gonghap_food_pattern, text):
            return True, 'gonghap_food'

        # ⑥ 운세구 필터 (지명 오염)
        if re.search(self.unse_exclusion_pattern, text):
            return True, 'unse_location'

        return False, ''

    # === 이하 V7과 동일한 메서드들 ===

    def count_keywords(self, text: str, keywords: list, sajutest: str = None) -> Dict[str, int]:
        """키워드 카운팅"""
        counts = {}
        for kw in keywords:
            if kw == '사주':
                if sajutest and sajutest in ['keyword', 'cooccur', 'indie', 'postpos']:
                    has_pollution = any(blackword in text for blackword in self.saju_blacklist)
                    if not has_pollution:
                        count = text.count('사주')
                        if count > 0:
                            counts['사주'] = count
            elif kw == '타로':
                if not re.search(self.taro_exclusion_pattern, text):
                    count = text.count('타로')
                    if count > 0:
                        counts['타로'] = count
            else:
                count = text.count(kw)
                if count > 0:
                    counts[kw] = count

        sorted_counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
        return sorted_counts

    def format_word_counts(self, counts: Dict[str, int]) -> str:
        """카운트 딕셔너리를 문자열로 포맷"""
        if not counts:
            return ""
        return ", ".join([f"{k}:{v}" for k, v in counts.items()])

    def validate_saju_pipeline(self, text: str) -> str:
        """'사주' 4단계 파이프라인 검증"""
        for blackword in self.saju_blacklist:
            if blackword in text:
                return 'notsaju'

        for brand in self.saju_brands:
            if brand in text:
                return 'keyword'
        for compound in self.saju_compounds:
            if compound in text:
                return 'keyword'

        for word in self.saju_cooccur_words:
            if word in text:
                return 'cooccur'

        if re.search(r'사주 (?!하|시키)', text):
            return 'indie'

        if re.search(self.saju_postposition_pattern, text):
            if '사주를' in text or '사주한' in text or '사주하' in text:
                return 'notsaju'
            return 'postpos'
        if re.search(self.saju_attachment_pattern, text):
            return 'postpos'

        if re.search(self.saju_exclusion_pattern, text):
            return 'notsaju'

        return 'notsaju'

    def validate_taro(self, text: str) -> dict:
        """'타로' 엄격한 검증"""
        if '타로' not in text:
            return {'valid': False, 'reason': 'no_taro'}

        if re.search(self.taro_exclusion_pattern, text):
            return {'valid': False, 'reason': 'taro_pollution'}

        for pattern in self.taro_valid_patterns:
            if re.search(pattern, text):
                has_fortune_keyword = any(kw in text for kw in self.strict_cooccurrence["타로"])
                if has_fortune_keyword:
                    return {'valid': True, 'reason': 'taro_valid_with_cooccurrence'}
                else:
                    # 단독 타로는 2회 이상 등장해야 유효
                    if text.count('타로') >= 2:
                        return {'valid': True, 'reason': 'taro_valid_alone'}
                    else:
                        return {'valid': False, 'reason': 'taro_alone_single'}

        return {'valid': False, 'reason': 'taro_invalid_prefix'}

    def validate_gonghap(self, text: str) -> dict:
        """'궁합' 전용 검증 (strict 모드)"""
        if '궁합' not in text:
            return {'valid': False, 'reason': 'no_gonghap', 'downgrade': False}

        has_fortune_keyword = any(kw in text for kw in self.strict_cooccurrence["궁합"])

        if has_fortune_keyword:
            has_relationship_keyword = any(rel_kw in text for rel_kw in self.relationship_keywords)

            return {
                'valid': True,
                'reason': 'gonghap_with_fortune_keywords',
                'downgrade': has_relationship_keyword
            }
        else:
            return {'valid': False, 'reason': 'gonghap_alone', 'downgrade': False}

    def validate_other_keywords(self, text: str) -> dict:
        """'사주' 이외 키워드 검증"""
        matched_keywords = []
        all_religious_keywords = self.target_keywords | self.whitelist_core
        cooccurrence_count = sum(1 for kw in all_religious_keywords if kw in text)

        gonghap_result = self.validate_gonghap(text)
        if gonghap_result['valid']:
            return {
                'valid': True,
                'reason': gonghap_result['reason'],
                'matched_keywords': ['궁합'],
                'cooccurrence_count': cooccurrence_count,
                'downgrade': gonghap_result['downgrade']
            }

        taro_result = self.validate_taro(text)
        if taro_result['valid']:
            return {
                'valid': True,
                'reason': taro_result['reason'],
                'matched_keywords': ['타로'],
                'cooccurrence_count': cooccurrence_count,
                'downgrade': False
            }

        for keyword in self.regular_keywords:
            if keyword == "타로":
                continue
            if re.search(rf'\s{re.escape(keyword)}\s', f' {text} '):
                return {
                    'valid': True,
                    'reason': 'independent_word',
                    'matched_keywords': [keyword],
                    'cooccurrence_count': cooccurrence_count,
                    'downgrade': False
                }

        for keyword in self.regular_keywords:
            if keyword == "타로":
                continue
            pattern = rf'(?<![가-힣]){re.escape(keyword)}'
            if re.search(pattern, text):
                matched_keywords.append(keyword)
                if any(wl in text for wl in self.all_whitelist):
                    return {
                        'valid': True,
                        'reason': 'keyword_with_whitelist',
                        'matched_keywords': matched_keywords,
                        'cooccurrence_count': cooccurrence_count,
                        'downgrade': False
                    }

        found_keywords = []
        for keyword in self.regular_keywords:
            if keyword == "타로":
                continue
            pattern = rf'(?<![가-힣]){re.escape(keyword)}'
            if re.search(pattern, text):
                found_keywords.append(keyword)

        if len(found_keywords) >= 2:
            return {
                'valid': True,
                'reason': 'multiple_target_keywords',
                'matched_keywords': found_keywords,
                'cooccurrence_count': cooccurrence_count,
                'downgrade': False
            }

        for special_kw, required_kws in self.special_combinations.items():
            if special_kw in text:
                for req_kw in required_kws:
                    pattern = rf'(?<![가-힣]){re.escape(req_kw)}'
                    if re.search(pattern, text):
                        return {
                            'valid': True,
                            'reason': f'special_combination_{special_kw}',
                            'matched_keywords': [special_kw, req_kw],
                            'cooccurrence_count': cooccurrence_count,
                            'downgrade': False
                        }

        return {
            'valid': False,
            'reason': 'no_match',
            'matched_keywords': matched_keywords,
            'cooccurrence_count': cooccurrence_count,
            'downgrade': False
        }

    def calculate_validity_strength(self, brand_counts: Dict[str, int], fortune_counts: Dict[str, int]) -> int:
        """validity 강도 계산 (0-2)"""
        if len(brand_counts) >= 1:
            return 2

        if len(fortune_counts) >= 2:
            return 2

        return 1

    def validate_text(self, text: str) -> dict:
        """텍스트의 유효성 검증 + 키워드 카운팅 + 강도 계산"""
        if not isinstance(text, str):
            return {
                'valid': 0,
                'reason': 'invalid_text',
                'sajutest': 'nosaju',
                'brand_word': '',
                'fortune_word': '',
                'filtered': False,
                'filter_reason': ''
            }

        # === 0. 강한 패턴 우선 검증 (무조건 validity=2) ===
        for pattern in self.all_strong_patterns:
            if re.search(pattern, text):
                brand_counts = self.count_keywords(text, self.brand_keywords)
                fortune_counts = self.count_keywords(text, self.fortune_keywords, 'nosaju')
                return {
                    'valid': 2,
                    'reason': f'strong_pattern:{pattern}',
                    'sajutest': 'nosaju',
                    'brand_word': self.format_word_counts(brand_counts),
                    'fortune_word': self.format_word_counts(fortune_counts),
                    'filtered': False,
                    'filter_reason': ''
                }

        # === 0.5. 궁합 별도 검증 (co-occ 필요) ===
        if '궁합' in text:
            has_valid_cooccur = any(kw in text for kw in self.gunghap_valid_cooccur)
            if has_valid_cooccur:
                brand_counts = self.count_keywords(text, self.brand_keywords)
                fortune_counts = self.count_keywords(text, self.fortune_keywords, 'nosaju')
                validity_strength = self.calculate_validity_strength(brand_counts, fortune_counts)
                # 궁합 + 운세키워드 = 최소 V1, co-occ에 따라 V2 가능
                return {
                    'valid': max(1, validity_strength),
                    'reason': 'gunghap_with_cooccur',
                    'sajutest': 'nosaju',
                    'brand_word': self.format_word_counts(brand_counts),
                    'fortune_word': self.format_word_counts(fortune_counts),
                    'filtered': False,
                    'filter_reason': ''
                }
            # 궁합만 단독 등장 → 무시 (다른 키워드로 넘어감)

        # === 1. '사주' 최우선 검증 ===
        if '사주' in text:
            sajutest_result = self.validate_saju_pipeline(text)

            if sajutest_result in ['keyword', 'cooccur', 'indie', 'postpos']:
                brand_counts = self.count_keywords(text, self.brand_keywords)
                fortune_counts = self.count_keywords(text, self.fortune_keywords, sajutest_result)

                validity_strength = self.calculate_validity_strength(brand_counts, fortune_counts)

                # 명리 용어 co-occ 있으면 V2로 승격
                myungri_terms = ['명리', '명리학', '대운', '세운', '일주', '월주', '시주', '연주',
                                 '오행', '십신', '용신', '격국', '신강', '신약']
                if validity_strength < 2 and any(term in text for term in myungri_terms):
                    validity_strength = 2

                # saju_indie + AI 토큰 → ai_fortune V2
                if sajutest_result == 'indie':
                    text_lower = text.lower()
                    if any(token.lower() in text_lower for token in self.ai_tokens):
                        return {
                            'valid': 2,
                            'reason': 'ai_fortune',
                            'sajutest': sajutest_result,
                            'brand_word': self.format_word_counts(brand_counts),
                            'fortune_word': self.format_word_counts(fortune_counts),
                            'filtered': False,
                            'filter_reason': ''
                        }

                return {
                    'valid': validity_strength,
                    'reason': f'saju_{sajutest_result}',
                    'sajutest': sajutest_result,
                    'brand_word': self.format_word_counts(brand_counts),
                    'fortune_word': self.format_word_counts(fortune_counts),
                    'filtered': False,
                    'filter_reason': ''
                }
            else:
                sajutest_result = 'notsaju'
        else:
            sajutest_result = 'nosaju'

        # === 2. 다른 키워드 검증 ===
        other_result = self.validate_other_keywords(text)

        brand_counts = self.count_keywords(text, self.brand_keywords)
        fortune_counts = self.count_keywords(text, self.fortune_keywords, sajutest_result)

        if other_result['valid']:
            validity_strength = self.calculate_validity_strength(brand_counts, fortune_counts)

            if other_result.get('downgrade', False):
                validity_strength = 1

            # === 타로/신점/작명/운세 co-occ 승격 (V1 → V2) ===
            if validity_strength < 2:
                # 타로 + co-occ
                if '타로' in text and any(kw in text for kw in self.taro_cooccur_words):
                    validity_strength = 2
                # 신점 + co-occ
                elif '신점' in text and any(kw in text for kw in self.sinjeom_cooccur_words):
                    validity_strength = 2
                # 작명 + co-occ
                elif '작명' in text and any(kw in text for kw in self.jakming_cooccur_words):
                    validity_strength = 2
                # 운세 + co-occ (시간표현/서비스)
                elif '운세' in text and any(kw in text for kw in self.unse_cooccur_words):
                    validity_strength = 2

            return {
                'valid': validity_strength,
                'reason': other_result['reason'],
                'sajutest': sajutest_result,
                'brand_word': self.format_word_counts(brand_counts),
                'fortune_word': self.format_word_counts(fortune_counts),
                'filtered': False,
                'filter_reason': ''
            }
        else:
            return {
                'valid': 0,
                'reason': 'no_match',
                'sajutest': sajutest_result,
                'brand_word': self.format_word_counts(brand_counts),
                'fortune_word': self.format_word_counts(fortune_counts),
                'filtered': False,
                'filter_reason': ''
            }

    def process_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        DataFrame 전체 처리

        Returns:
            (valid_df, filtered_dfs)
            valid_df: 필터를 통과한 데이터
            filtered_dfs: {filter_reason: filtered_df} 딕셔너리
        """
        print(f"Processing {len(df)} rows...")

        # whole_content 사용 (제목+본문 이미 합쳐진 컬럼)
        if 'whole_content' in df.columns:
            combined_text = df['whole_content'].fillna('').astype(str)
        else:
            print("Error: 'whole_content' column not found")
            return df, {}

        # === 1. 필터링 체크 ===
        print("Checking filters...")
        filter_results = combined_text.apply(lambda x: self.check_filters(x))

        filtered_mask = filter_results.apply(lambda x: x[0])
        filter_reasons = filter_results.apply(lambda x: x[1])

        # 필터링된 데이터와 통과한 데이터 분리
        filtered_df = df[filtered_mask].copy()
        filtered_df['filter_reason'] = filter_reasons[filtered_mask]

        valid_df = df[~filtered_mask].copy()
        valid_combined_text = combined_text[~filtered_mask]

        print(f"  Filtered out: {len(filtered_df)} rows")
        print(f"  Passed filters: {len(valid_df)} rows")

        # 필터 이유별로 분류
        filtered_dfs = {}
        if len(filtered_df) > 0:
            for reason in filtered_df['filter_reason'].unique():
                filtered_dfs[reason] = filtered_df[filtered_df['filter_reason'] == reason]
                print(f"    - {reason}: {len(filtered_dfs[reason])} rows")

        # === 2. 통과한 데이터만 검증 수행 ===
        if len(valid_df) > 0:
            print("Validating passed data...")
            results = valid_combined_text.apply(self.validate_text)

            # 결과 DataFrame 생성
            keep_cols = ['url', '사이트', '작성날짜', 'whole_content']
            if 'views' in valid_df.columns:
                keep_cols.append('views')
            keep_cols = [c for c in keep_cols if c in valid_df.columns]
            result_df = valid_df[keep_cols].copy() if keep_cols else valid_df.copy()

            result_df['brand.word'] = results.apply(lambda x: x['brand_word'])
            result_df['fortune.word'] = results.apply(lambda x: x['fortune_word'])
            result_df['validity'] = results.apply(lambda x: x['valid'])
            result_df['validity_reason'] = results.apply(lambda x: x['reason'])
            result_df['sajutest'] = results.apply(lambda x: x['sajutest'])

            # 통계 출력
            total_count = len(result_df)
            strong_valid_count = (result_df['validity'] == 2).sum()
            valid_count = (result_df['validity'] == 1).sum()
            invalid_count = (result_df['validity'] == 0).sum()

            print(f"\nValidation Results:")
            print(f"Strong Valid (2): {strong_valid_count} ({strong_valid_count/total_count*100:.1f}%)")
            print(f"Valid (1): {valid_count} ({valid_count/total_count*100:.1f}%)")
            print(f"Invalid (0): {invalid_count} ({invalid_count/total_count*100:.1f}%)")
            print(f"Total Valid (1+2): {strong_valid_count + valid_count} ({(strong_valid_count + valid_count)/total_count*100:.1f}%)")

            return result_df, filtered_dfs
        else:
            return pd.DataFrame(), filtered_dfs

    def process_file(self, input_path: Path, output_folder: Path):
        """단일 CSV 파일 처리"""
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
                print(f"  [WARN] Empty file: {input_path.name}")
                return None, {}, None

            print(f"\n{'='*60}")
            print(f"Processing: {input_path.name}")
            print(f"{'='*60}")

            # 처리
            original_count = len(df)
            result_df, filtered_dfs = self.process_dataframe(df)

            # 필터링된 데이터 저장
            for reason, filt_df in filtered_dfs.items():
                # Windows 파일명 금지 문자 모두 제거/치환 + 백슬래시도 제거 (정규식 패턴 때문에)
                safe_reason = (reason.replace(':', '_').replace('/', '_').replace('\\', '_')
                              .replace('?', '').replace('!', '').replace('[', '').replace(']', '')
                              .replace('{', '').replace('}', '').replace('*', '').replace('<', '')
                              .replace('>', '').replace('|', '').replace('"', '').replace(',', '_')
                              .replace('+', '_').replace(' ', '_').replace('(', '').replace(')', ''))
                filter_filename = f'filtered_by_{safe_reason}.csv'
                filter_path = output_folder / filter_filename

                # 덮어쓰기 (중복 방지)
                filt_df.drop(columns=['filter_reason']).to_csv(filter_path, index=False, encoding='utf-8-sig')

                print(f"  └─ Filter saved: {filter_filename}")

            # 검증 결과 저장
            if len(result_df) > 0:
                output_filename = input_path.stem.replace('_normalized', '') + '_verified_v8.csv'
                output_path = output_folder / output_filename

                result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"[OK] Saved: {output_filename}")

            # 통계 정보 생성
            file_stats = {
                '파일명': input_path.name,
                '총_행수': original_count,
                '필터링됨': sum(len(fdf) for fdf in filtered_dfs.values()),
                '통과': len(result_df) if result_df is not None else 0,
            }

            if len(result_df) > 0:
                file_stats['V2_강함'] = (result_df['validity'] == 2).sum()
                file_stats['V1_보통'] = (result_df['validity'] == 1).sum()
                file_stats['V0_무효'] = (result_df['validity'] == 0).sum()
                file_stats['V2_비율'] = round(file_stats['V2_강함'] / len(result_df) * 100, 1)
                file_stats['V1_비율'] = round(file_stats['V1_보통'] / len(result_df) * 100, 1)
                file_stats['V0_비율'] = round(file_stats['V0_무효'] / len(result_df) * 100, 1)
            else:
                file_stats.update({'V2_강함': 0, 'V1_보통': 0, 'V0_무효': 0, 'V2_비율': 0, 'V1_비율': 0, 'V0_비율': 0})

            return result_df, filtered_dfs, file_stats

        except Exception as e:
            print(f"X Error processing {input_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return None, {}, None

    def merge_and_filter_by_validity(self, output_folder: Path, all_results: list):
        """모든 결과를 합쳐서 validity별로 필터링한 파일 생성"""
        if not all_results:
            print("No results to merge.")
            return

        print(f"\nMerging {len(all_results)} files...")
        merged_df = pd.concat(all_results, ignore_index=True)

        validity_2 = merged_df[merged_df['validity'] == 2]
        validity_1 = merged_df[merged_df['validity'] == 1]
        validity_0 = merged_df[merged_df['validity'] == 0]

        if len(validity_2) > 0:
            output_path = output_folder / 'validity_2_strong.csv'
            validity_2.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"[OK] Saved validity=2 (strong): {len(validity_2)} rows -> validity_2_strong.csv")

            if 'url' in validity_2.columns:
                validity_2_no_url = validity_2.drop(columns=['url'])
                output_path_no_url = output_folder / 'validity_2_strong_no_url.csv'
                validity_2_no_url.to_csv(output_path_no_url, index=False, encoding='utf-8-sig')
                print(f"  └─ No-URL version: validity_2_strong_no_url.csv")

        if len(validity_1) > 0:
            output_path = output_folder / 'validity_1_normal.csv'
            validity_1.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"[OK] Saved validity=1 (normal): {len(validity_1)} rows -> validity_1_normal.csv")

            if 'url' in validity_1.columns:
                validity_1_no_url = validity_1.drop(columns=['url'])
                output_path_no_url = output_folder / 'validity_1_normal_no_url.csv'
                validity_1_no_url.to_csv(output_path_no_url, index=False, encoding='utf-8-sig')
                print(f"  └─ No-URL version: validity_1_normal_no_url.csv")

        if len(validity_0) > 0:
            output_path = output_folder / 'validity_0_invalid.csv'
            validity_0.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"[OK] Saved validity=0 (invalid): {len(validity_0)} rows -> validity_0_invalid.csv")

            if 'url' in validity_0.columns:
                validity_0_no_url = validity_0.drop(columns=['url'])
                output_path_no_url = output_folder / 'validity_0_invalid_no_url.csv'
                validity_0_no_url.to_csv(output_path_no_url, index=False, encoding='utf-8-sig')
                print(f"  └─ No-URL version: validity_0_invalid_no_url.csv")

        print(f"\nMerge Summary:")
        print(f"  Total rows: {len(merged_df)}")
        print(f"  Strong Valid (2): {len(validity_2)}")
        print(f"  Normal Valid (1): {len(validity_1)}")
        print(f"  Invalid (0): {len(validity_0)}")

    def process_folder(self, folder_path: str, part: int = None):
        """폴더 내 모든 normalized CSV 파일 처리

        Args:
            folder_path: 처리할 폴더 경로
            part: 1 또는 2 (병렬 처리용), None이면 전체 처리
        """
        folder = Path(folder_path)

        if not folder.exists():
            print(f"Error: Folder '{folder_path}' does not exist.")
            return

        # 입력/출력 폴더 설정
        input_folder = folder / '1_normalized'

        if part == 1:
            output_folder = folder / '2_validity_part1'
        elif part == 2:
            output_folder = folder / '2_validity_part2'
        else:
            output_folder = folder / '2_validity'

        output_folder.mkdir(exist_ok=True)

        if not input_folder.exists():
            print(f"Error: Input folder '1_normalized' does not exist.")
            return

        part_msg = f" (Part {part})" if part else ""
        print(f"\n{'='*70}")
        print(f"ChiefValidator V9 - 병렬 처리{part_msg}")
        print(f"Source: {input_folder}")
        print(f"Output: {output_folder}")
        print(f"{'='*70}\n")

        csv_files = list(input_folder.glob('*_merged.csv'))

        # 파일 리스트 분할 (part 지정 시)
        if part == 1:
            csv_files = csv_files[:len(csv_files)//2]
            print(f"Processing first half: {len(csv_files)} files")
        elif part == 2:
            csv_files = csv_files[len(csv_files)//2:]
            print(f"Processing second half: {len(csv_files)} files")

        if not csv_files:
            print("No normalized CSV files found.")
            return

        print(f"Found {len(csv_files)} normalized files\n")

        success = 0
        fail = 0
        all_results = []
        all_stats = []

        for csv_file in csv_files:
            result_df, filtered_dfs, file_stats = self.process_file(csv_file, output_folder)
            if result_df is not None and len(result_df) > 0:
                success += 1
                all_results.append(result_df)
            else:
                fail += 1

            if file_stats is not None:
                all_stats.append(file_stats)

        print(f"\n{'='*70}")
        print(f"Individual File Processing Complete!")
        print(f"  Success: {success}")
        print(f"  Failed: {fail}")
        print(f"  Total: {len(csv_files)}")
        print(f"{'='*70}")

        # validity별 필터링 파일 생성
        if all_results:
            self.merge_and_filter_by_validity(output_folder, all_results)

        # 통계 요약 파일 저장
        if all_stats:
            summary_df = pd.DataFrame(all_stats)
            summary_path = output_folder / 'validation_summary.csv'
            summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
            print(f"\n[OK] Validation Summary saved: validation_summary.csv")

        print(f"\n{'='*70}")
        print(f"All Processing Complete!")
        print(f"Output folder: {output_folder}")
        print(f"Check 'filtered_by_*.csv' files for review")
        print(f"{'='*70}\n")


def main():
    """메인 실행 함수"""
    # 커맨드라인 인자 파싱
    part = None
    if len(sys.argv) > 2 and sys.argv[1] == '--part':
        try:
            part = int(sys.argv[2])
            if part not in [1, 2]:
                print("Error: --part must be 1 or 2")
                print("Usage: python cv9.py --part 1  (또는 --part 2)")
                return
        except ValueError:
            print("Error: --part argument must be a number (1 or 2)")
            return

    validator = ReligiousServiceValidator()
    current_folder = os.path.dirname(os.path.abspath(__file__))
    validator.process_folder(current_folder, part=part)

    # 완료 알림 (비프음 3회)
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 300)
    except:
        # winsound 실패 시 터미널 벨로 폴백
        print("\a" * 3)

    print("🔔 처리 완료!")


if __name__ == "__main__":
    main()
