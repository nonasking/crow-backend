"""normalize_merchant 단위 테스트.

순수 정규식 로직이므로 DB가 필요 없다. 명세(01_analyst_requirements.md)의
예시 전부 + 비매칭 원본 유지 + 멱등성을 검증한다.
"""

import pytest

from receivers.services import normalize_merchant


class TestNormalizeMerchantSpecExamples:
    """명세에 명시된 변환 예시 (작업1·공통 정규화)."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            # 명세 예시 그대로
            ("(일시불)06/20 카페63도", "카페63도"),
            ("(일시불)05/31 18:28 홈플러스익스", "홈플러스익스"),
            ("(할부3개월)06/03 20:52 (주)이마트", "이마트"),
            # 웹훅 회귀 테스트의 신한 케이스(누적 절단 후 normalize 입력)
            ("(일시불)02/23 16:56 세븐일레븐영", "세븐일레븐영"),
        ],
    )
    def test_spec_examples(self, raw, expected):
        assert normalize_merchant(raw) == expected


class TestNormalizeMerchantMarkers:
    """마커(일시불/할부 변형)와 날짜/시간 조합 처리."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            # 시간 없음
            ("(일시불)06/20 카페63도", "카페63도"),
            # 시간 포함
            ("(일시불)05/31 18:28 홈플러스익스", "홈플러스익스"),
            # 할부 N개월
            ("(할부3개월)06/03 20:52 스타벅스", "스타벅스"),
            ("(할부12개월)12/01 09:05 쿠팡", "쿠팡"),
            # 할부 (개월 없는 변형) - 정규식 할부[^)]* 가 빈 문자열도 허용
            ("(할부)06/03 다이소", "다이소"),
            # 한 자리 월/일
            ("(일시불)1/2 GS25", "GS25"),
            # 한 자리 시도 허용되는지 (HH 1~2자리)
            ("(일시불)06/20 9:05 편의점", "편의점"),
        ],
    )
    def test_markers_and_dates(self, raw, expected):
        assert normalize_merchant(raw) == expected


class TestNormalizeMerchantCorporateForm:
    """법인격 표기 제거 + 공백 collapse."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("(할부3개월)06/03 20:52 (주)이마트", "이마트"),
            ("(일시불)06/20 주식회사카카오", "카카오"),
            ("(일시불)06/20 ㈜네이버", "네이버"),
            # 법인격이 가운데 끼어 공백이 생기는 경우 collapse 되어야 함
            ("(일시불)06/20 (주) 홈플러스", "홈플러스"),
        ],
    )
    def test_corporate_form_removed(self, raw, expected):
        assert normalize_merchant(raw) == expected

    def test_whitespace_collapsed_and_stripped(self):
        # 다중 공백 -> 단일 공백 + strip
        assert normalize_merchant("(일시불)06/20   카페   63도  ") == "카페 63도"


class TestNormalizeMerchantNonMatching:
    """SMS 포맷이 아닌 입력은 원본 그대로 반환해야 한다 (절대 미변경 보장)."""

    @pytest.mark.parametrize(
        "raw",
        [
            "식재료",            # PLAIN
            "설명_가맹점",        # OLD 포맷
            "잔액 2,311,720원",  # 잔액/비거래 행
            "세븐일레븐",         # 이미 정규화된 일반 문자열
            "(주)이마트",         # 마커/날짜 없이 법인격만 — SMS 포맷 아님 → 미변경
            "(일시불)카페63도",   # 날짜가 없으면 패턴 불일치 → 미변경
        ],
    )
    def test_non_matching_returns_original(self, raw):
        assert normalize_merchant(raw) == raw

    def test_empty_string_returns_empty(self):
        assert normalize_merchant("") == ""

    def test_none_safe(self):
        # if not item: return item — None 입력도 폭발하지 않고 그대로 반환
        assert normalize_merchant(None) is None


class TestNormalizeMerchantIdempotency:
    """멱등성: 정규화 결과를 다시 넣어도 불변이어야 한다 (마이그레이션 재실행 안전)."""

    @pytest.mark.parametrize(
        "raw",
        [
            "(일시불)06/20 카페63도",
            "(일시불)05/31 18:28 홈플러스익스",
            "(할부3개월)06/03 20:52 (주)이마트",
            "식재료",
            "잔액 2,311,720원",
            "",
        ],
    )
    def test_idempotent(self, raw):
        once = normalize_merchant(raw)
        twice = normalize_merchant(once)
        assert once == twice
