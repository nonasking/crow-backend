"""지출 요약의 '오늘' 기준 테스트.

서버 TIME_ZONE은 UTC지만 '오늘'은 한국 시간 기준이어야 한다.
KST 2026-11-01 00:30은 UTC로 아직 2026-10-31 15:30이다.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from expenses.constants import LOCAL_TIMEZONE
from expenses.models import Budget
from expenses.serializers.api_serializers import ExpenseSummarySerializer
from expenses.services.expense_summary_service import summarize_expenses

KST_JUST_AFTER_MIDNIGHT = datetime(2026, 11, 1, 0, 30, tzinfo=LOCAL_TIMEZONE)


def test_summary_defaults_to_kst_year_month():
    with patch("django.utils.timezone.now", return_value=KST_JUST_AFTER_MIDNIGHT):
        serializer = ExpenseSummarySerializer(data={})
        assert serializer.is_valid(), serializer.errors

    assert serializer.validated_data["year"] == 2026
    assert serializer.validated_data["month"] == 11


@pytest.mark.django_db
def test_daily_budget_prorates_to_kst_today():
    Budget.objects.create(year=2026, month=11, amount=30000)

    with patch("django.utils.timezone.now", return_value=KST_JUST_AFTER_MIDNIGHT):
        result = summarize_expenses(year=2026, month=11)

    # 11월 1일치(30000 / 30일 * 1일)
    assert result["daily_budget"] == 1000


@pytest.mark.django_db
@pytest.mark.parametrize(
    "year, month, expected",
    [
        (2026, 10, 31000),  # 지난 달: 한 달 전체
        (2026, 11, 1000),  # 이번 달: 오늘(1일)까지
        (2026, 12, 0),  # 앞으로 올 달: 0일
    ],
)
def test_daily_budget_prorates_by_month_position(year, month, expected):
    Budget.objects.create(year=year, month=month, amount=31000 if month != 11 else 30000)

    with patch("django.utils.timezone.now", return_value=KST_JUST_AFTER_MIDNIGHT):
        result = summarize_expenses(year=year, month=month)

    assert result["daily_budget"] == expected


@pytest.mark.parametrize("month", [0, 13])
def test_summary_rejects_out_of_range_month(month):
    serializer = ExpenseSummarySerializer(data={"year": 2026, "month": month})
    assert not serializer.is_valid()
    assert "month" in serializer.errors
