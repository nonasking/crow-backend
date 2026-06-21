"""auto_classify_unsettled management command 테스트.

커맨드는 출력/옵션 라우팅만 담당(로직은 service). 여기선 옵션이
서비스 동작과 DB 상태에 올바르게 연결되는지 검증한다.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from expenses.constants import ExpenseCategoryEnum as Cat
from expenses.constants import ExpenseSubCategoryEnum as Sub
from expenses.models import Expense


def _make(item, category, sub_category, auto_classified=False):
    return Expense.objects.create(
        spent_at="2024-06-20",
        category=category,
        sub_category=sub_category,
        item=item,
        payment_method="SHINHAN",
        amount=1000,
        auto_classified=auto_classified,
    )


@pytest.mark.django_db
class TestAutoClassifyUnsettledCommand:

    def _run(self, *args):
        out = StringIO()
        call_command("auto_classify_unsettled", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_default_does_not_mutate(self):
        # P2: 기본(dry-run) DB 미변경
        _make("스타벅스", Cat.FOOD, Sub.BEVERAGE)
        _make("스타벅스", Cat.FOOD, Sub.BEVERAGE)
        u = _make("스타벅스", Cat.UNSETTLED, Sub.UNSETTLED)

        output = self._run()

        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED
        assert u.auto_classified is False
        assert "DRY-RUN" in output
        assert "매칭(자동분류 대상): 1건" in output

    def test_apply_mutates_matched_only(self):
        # P0/P2: --apply 가 매칭분만 분류
        _make("스타벅스", Cat.FOOD, Sub.BEVERAGE)
        _make("스타벅스", Cat.FOOD, Sub.BEVERAGE)
        matched = _make("스타벅스", Cat.UNSETTLED, Sub.UNSETTLED)
        # 신규 UNSETTLED — 변경되면 안 됨
        new_row = _make("신규가맹점XYZ", Cat.UNSETTLED, Sub.UNSETTLED)

        output = self._run("--apply")

        matched.refresh_from_db()
        new_row.refresh_from_db()
        assert matched.category == Cat.FOOD
        assert matched.auto_classified is True
        assert new_row.category == Cat.UNSETTLED
        assert new_row.auto_classified is False
        assert "APPLY" in output
        assert "적용 완료: 1건" in output

    def test_min_count_option_filters_rules(self):
        # P1: --min-count 3 이면 2건 분포는 규칙 미채택
        _make("카페", Cat.FOOD, Sub.BEVERAGE)
        _make("카페", Cat.FOOD, Sub.BEVERAGE)
        u = _make("카페", Cat.UNSETTLED, Sub.UNSETTLED)

        self._run("--min-count", "3", "--apply")

        u.refresh_from_db()
        assert u.category == Cat.UNSETTLED  # 미채택 -> 미변경

    def test_revert_option_restores_auto_only(self):
        # P0: --revert 는 auto_classified=True 만 복원
        auto = _make("자동", Cat.FOOD, Sub.BEVERAGE, auto_classified=True)
        manual = _make("수동", Cat.FOOD, Sub.BEVERAGE, auto_classified=False)

        output = self._run("--revert")

        auto.refresh_from_db()
        manual.refresh_from_db()
        assert auto.category == Cat.UNSETTLED
        assert auto.auto_classified is False
        assert manual.category == Cat.FOOD
        assert manual.auto_classified is False
        assert "복원 완료: 1건" in output

    def test_no_match_reports_zero(self):
        _make("외톨이가맹점", Cat.UNSETTLED, Sub.UNSETTLED)
        output = self._run()
        assert "매칭(자동분류 대상): 0건" in output
        assert "매칭된 항목이 없습니다." in output
