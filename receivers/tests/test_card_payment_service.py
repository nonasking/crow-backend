from datetime import date, datetime
from unittest.mock import patch

import pytest

from expenses.constants import LOCAL_TIMEZONE, ExpensePaymentMethodEnum
from expenses.models import Expense
from receivers.services.card_payment_service import (
    record_card_payment,
    resolve_spent_at,
)


class TestResolveSpentAt:
    def test_past_date_uses_this_year(self):
        assert resolve_spent_at("02/23", today=date(2026, 3, 1)) == date(2026, 2, 23)

    def test_today_uses_this_year(self):
        assert resolve_spent_at("03/01", today=date(2026, 3, 1)) == date(2026, 3, 1)

    def test_future_date_uses_last_year(self):
        # 연초에 작년 연말 결제 문자를 받은 경우
        assert resolve_spent_at("12/31", today=date(2027, 1, 2)) == date(2026, 12, 31)

    def test_leap_day_missing_this_year_does_not_raise(self):
        # 2029년엔 2/29가 없으므로 작년(2028) 날짜로 해석
        assert resolve_spent_at("02/29", today=date(2029, 3, 10)) == date(2028, 2, 29)

    def test_today_defaults_to_kst_not_utc(self):
        # KST 2026-10-31 00:12 (UTC로는 아직 10/30) 에 받은 10/31 결제 문자
        now = datetime(2026, 10, 31, 0, 12, tzinfo=LOCAL_TIMEZONE)
        with patch("django.utils.timezone.now", return_value=now):
            assert resolve_spent_at("10/31") == date(2026, 10, 31)

    @pytest.mark.parametrize("spent_at", ["", "0223", "13/01", "02/23/01"])
    def test_unparsable_falls_back_to_today(self, spent_at):
        assert resolve_spent_at(spent_at, today=date(2026, 3, 1)) == date(2026, 3, 1)


@pytest.mark.django_db
class TestRecordCardPayment:
    PARSED = {
        "amount": 2400,
        "item": "세븐일레븐영",
        "payment_method": ExpensePaymentMethodEnum.SHINHAN.value,
        "spent_at": "02/23",
    }

    def test_notion_and_expense_get_same_date(self):
        with patch(
            "receivers.externals.notion.api_client.NotionClient.create_card_record"
        ) as mock_create:
            expense = record_card_payment(dict(self.PARSED))

        notion_record = mock_create.call_args.args[0]
        expense.refresh_from_db()
        assert notion_record["spent_at"] == expense.spent_at
        assert notion_record["payment_method"] == ExpensePaymentMethodEnum.SHINHAN.label
        assert expense.payment_method == ExpensePaymentMethodEnum.SHINHAN

    def test_notion_failure_does_not_create_expense(self):
        with patch(
            "receivers.externals.notion.api_client.NotionClient.create_card_record",
            side_effect=RuntimeError("down"),
        ):
            with pytest.raises(RuntimeError):
                record_card_payment(dict(self.PARSED))

        assert not Expense.objects.exists()
