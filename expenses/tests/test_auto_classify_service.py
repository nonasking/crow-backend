"""auto_classify_service 테스트.

학습/매칭/복원의 안전·정확성을 검증한다.
- 에코방지: auto_classified=True 행은 학습에서 제외.
- 규칙 채택 경계: 단일분포 채택 / 모호 제외 / 저빈도 제외 / 짧은키 제외.
- classify_unsettled: dry-run 미변경, apply는 매칭분만 변경 + UNSETTLED 외 불변.
- revert: auto_classified=True만 복원, 수동분 미변경.

fixture item 은 SMS 포맷이 아닌 평문을 쓴다(normalize_merchant 가 원본 그대로 반환).
"""

import pytest

from expenses.constants import ExpenseCategoryEnum as Cat
from expenses.constants import ExpenseSubCategoryEnum as Sub
from expenses.models import Expense
from expenses.services.auto_classify_service import (
    build_deterministic_rules,
    classify_unsettled,
    revert_auto_classified,
)


def _make(item, category, sub_category, auto_classified=False, amount=1000):
    return Expense.objects.create(
        spent_at="2024-06-20",
        category=category,
        sub_category=sub_category,
        item=item,
        payment_method="SHINHAN",
        amount=amount,
        auto_classified=auto_classified,
    )


def _manual(item, category, sub_category, n=2):
    """수동 확정분 n건 생성 (학습 대상)."""
    return [_make(item, category, sub_category) for _ in range(n)]


def _unsettled(item, n=1):
    return [
        _make(item, Cat.UNSETTLED, Sub.UNSETTLED) for _ in range(n)
    ]


# ─────────────────────────────────────────────────────────
# build_deterministic_rules
# ─────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestBuildDeterministicRules:

    def test_single_distribution_adopted(self):
        # P1: 단일 분포 + count>=min_count -> 채택
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        rules = build_deterministic_rules(min_count=2)
        assert rules.get("스타벅스") == (Cat.FOOD, Sub.BEVERAGE)

    def test_ambiguous_distribution_excluded(self):
        # P1: 같은 키에 라벨 2종 -> 모호 -> 제외
        _make("이마트", Cat.FOOD, Sub.COOKING)
        _make("이마트", Cat.HOUSEHOLD, Sub.HOUSEHOLD)
        rules = build_deterministic_rules(min_count=1)
        assert "이마트" not in rules

    def test_low_frequency_excluded(self):
        # P1: 단일 분포지만 count(1) < min_count(2) -> 제외
        _make("저빈도가맹점", Cat.FOOD, Sub.BEVERAGE)
        rules = build_deterministic_rules(min_count=2)
        assert "저빈도가맹점" not in rules

    def test_low_frequency_adopted_when_min_count_lowered(self):
        _make("저빈도가맹점", Cat.FOOD, Sub.BEVERAGE)
        rules = build_deterministic_rules(min_count=1)
        assert rules.get("저빈도가맹점") == (Cat.FOOD, Sub.BEVERAGE)

    def test_short_key_excluded(self):
        # P1: len(key) < 2 -> 제외 ("A" 는 1글자)
        _manual("A", Cat.FOOD, Sub.BEVERAGE, n=5)
        rules = build_deterministic_rules(min_count=2)
        assert "A" not in rules

    def test_unsettled_rows_not_learned(self):
        # P1: UNSETTLED 행은 학습 대상 아님
        _make("미정산가맹점", Cat.UNSETTLED, Sub.UNSETTLED)
        _make("미정산가맹점", Cat.UNSETTLED, Sub.UNSETTLED)
        rules = build_deterministic_rules(min_count=1)
        assert "미정산가맹점" not in rules

    def test_auto_classified_rows_excluded_from_learning(self):
        # P0 에코방지: auto_classified=True 행만 있으면 규칙 생성 안 됨
        _make("자동분류가맹점", Cat.FOOD, Sub.BEVERAGE, auto_classified=True)
        _make("자동분류가맹점", Cat.FOOD, Sub.BEVERAGE, auto_classified=True)
        rules = build_deterministic_rules(min_count=1)
        assert "자동분류가맹점" not in rules

    def test_echo_chamber_auto_rows_do_not_break_manual_distribution(self):
        # P0 에코방지: 수동분(단일)에 다른 라벨의 auto 행이 섞여도
        # auto 는 제외되므로 규칙은 수동분 분포만 반영.
        _manual("혼합가맹점", Cat.FOOD, Sub.BEVERAGE, n=2)
        # 만약 auto 행이 학습되면 분포가 모호해져 규칙이 사라질 것.
        _make("혼합가맹점", Cat.HOUSEHOLD, Sub.HOUSEHOLD, auto_classified=True)
        _make("혼합가맹점", Cat.HOUSEHOLD, Sub.HOUSEHOLD, auto_classified=True)
        rules = build_deterministic_rules(min_count=2)
        assert rules.get("혼합가맹점") == (Cat.FOOD, Sub.BEVERAGE)


# ─────────────────────────────────────────────────────────
# classify_unsettled — dry-run / apply
# ─────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestClassifyUnsettled:

    def test_dry_run_does_not_mutate_db(self):
        # P2: dry-run 은 DB 미변경
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        u = _unsettled("스타벅스", n=1)[0]

        report = classify_unsettled(min_count=2, apply=False)

        assert report["matched_count"] == 1
        assert report["applied"] == 0
        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED
        assert u.sub_category == Sub.UNSETTLED
        assert u.auto_classified is False

    def test_apply_sets_category_and_flag_on_matched(self):
        # P2: apply 는 매칭분만 분류 + auto_classified=True
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        u = _unsettled("스타벅스", n=1)[0]

        report = classify_unsettled(min_count=2, apply=True)

        assert report["applied"] == 1
        u.refresh_from_db()
        assert u.category == Cat.FOOD
        assert u.sub_category == Sub.BEVERAGE
        assert u.auto_classified is True

    def test_apply_does_not_change_ambiguous_unsettled(self):
        # P0: 모호(다분포) UNSETTLED 는 apply 후에도 미변경
        _make("이마트", Cat.FOOD, Sub.COOKING)
        _make("이마트", Cat.HOUSEHOLD, Sub.HOUSEHOLD)
        u = _unsettled("이마트", n=1)[0]

        report = classify_unsettled(min_count=1, apply=True)

        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED
        assert u.auto_classified is False
        assert "이마트" in report["ambiguous"]

    def test_apply_does_not_change_new_unsettled(self):
        # P0: 신규(이력 없음) UNSETTLED 는 apply 후에도 미변경, new 로 분류
        u = _unsettled("처음보는가맹점", n=1)[0]

        report = classify_unsettled(min_count=2, apply=True)

        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED
        assert u.auto_classified is False
        assert "처음보는가맹점" in report["new"]
        assert "처음보는가맹점" not in report["ambiguous"]

    def test_low_frequency_unsettled_is_ambiguous_not_new(self):
        # P1: 이력은 있으나 저빈도라 규칙 미채택 -> ambiguous
        _make("저빈도", Cat.FOOD, Sub.BEVERAGE)  # 1건뿐, min_count=2 미달
        u = _unsettled("저빈도", n=1)[0]

        report = classify_unsettled(min_count=2, apply=True)

        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED
        assert "저빈도" in report["ambiguous"]
        assert "저빈도" not in report["new"]

    def test_non_unsettled_rows_untouched_by_apply(self):
        # P0/P1: UNSETTLED 외 행은 apply 가 절대 건드리지 않음
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        # 다른 수동분 (UNSETTLED 아님)
        manual_row = _make("스타벅스", Cat.FOOD, Sub.BEVERAGE)
        # 키가 같은 비-UNSETTLED 행이라도 변경되면 안 됨
        before = (manual_row.category, manual_row.sub_category, manual_row.auto_classified)

        classify_unsettled(min_count=2, apply=True)

        manual_row.refresh_from_db()
        after = (manual_row.category, manual_row.sub_category, manual_row.auto_classified)
        assert before == after
        assert manual_row.auto_classified is False

    def test_idempotent_rerun_no_reprocess(self):
        # P2: apply 재실행 시 이미 분류된 건은 UNSETTLED 아니므로 재처리 0
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        _unsettled("스타벅스", n=1)

        first = classify_unsettled(min_count=2, apply=True)
        assert first["applied"] == 1

        second = classify_unsettled(min_count=2, apply=True)
        assert second["applied"] == 0
        assert second["matched_count"] == 0
        assert second["total_unsettled"] == 0

    def test_report_counts_consistency(self):
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        _unsettled("스타벅스", n=2)
        _unsettled("처음보는가맹점", n=1)

        report = classify_unsettled(min_count=2, apply=False)

        assert report["total_unsettled"] == 3
        assert report["matched_count"] == 2
        assert report["unmatched_count"] == 1
        assert report["rules_count"] == 1


# ─────────────────────────────────────────────────────────
# revert_auto_classified
# ─────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRevertAutoClassified:

    def test_reverts_only_auto_classified(self):
        # P0: auto_classified=True 만 UNSETTLED/UNSETTLED/False 로 복원
        auto = _make("자동가맹점", Cat.FOOD, Sub.BEVERAGE, auto_classified=True)

        count = revert_auto_classified()

        assert count == 1
        auto.refresh_from_db()
        assert auto.category == Cat.UNSETTLED
        assert auto.sub_category == Sub.UNSETTLED
        assert auto.auto_classified is False

    def test_manual_rows_untouched(self):
        # P0: 수동분(auto_classified=False)은 절대 미변경
        manual = _make("수동가맹점", Cat.FOOD, Sub.BEVERAGE, auto_classified=False)

        revert_auto_classified()

        manual.refresh_from_db()
        assert manual.category == Cat.FOOD
        assert manual.sub_category == Sub.BEVERAGE
        assert manual.auto_classified is False

    def test_revert_returns_zero_when_nothing_auto(self):
        _make("수동가맹점", Cat.FOOD, Sub.BEVERAGE, auto_classified=False)
        assert revert_auto_classified() == 0

    def test_apply_then_revert_roundtrip(self):
        _manual("스타벅스", Cat.FOOD, Sub.BEVERAGE, n=2)
        u = _unsettled("스타벅스", n=1)[0]

        classify_unsettled(min_count=2, apply=True)
        u.refresh_from_db()
        assert u.auto_classified is True

        reverted = revert_auto_classified()
        assert reverted == 1
        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED
        assert u.sub_category == Sub.UNSETTLED
        assert u.auto_classified is False
