from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from expenses.constants import LOCAL_TIMEZONE, ExpensePaymentMethodEnum
from expenses.models import Expense
from receivers.externals.exchange_rate.api_client import ExchangeRateError
from receivers.services.card_payment_service import (
    convert_foreign_amount,
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


GET_KRW_RATE = (
    "receivers.externals.exchange_rate.api_client.ExchangeRateClient.get_krw_rate"
)
NOTION_CREATE = "receivers.externals.notion.api_client.NotionClient.create_card_record"
FOREIGN_PARSED = {
    "amount": None,
    "item": "ANTHROPIC*",
    "payment_method": ExpensePaymentMethodEnum.SHINHAN.value,
    "spent_at": "11/11",
    "foreign_amount": Decimal("220.00"),
    "currency": "USD",
}


class TestConvertForeignAmount:
    def test_krw_parsed_passes_through_without_api_call(self):
        parsed = {"amount": 37730, "item": "ELEVENLABS", "payment_method": "SH", "spent_at": "11/11"}
        with patch(GET_KRW_RATE) as mock_rate:
            assert convert_foreign_amount(parsed) is parsed
        mock_rate.assert_not_called()

    def test_converts_with_rate_and_leaves_memo(self):
        with patch(GET_KRW_RATE, return_value=Decimal("1336.9")) as mock_rate:
            record = convert_foreign_amount(dict(FOREIGN_PARSED))

        mock_rate.assert_called_once_with("USD")
        assert record["amount"] == 294118  # 220.00 * 1336.9 = 294,118
        assert record["memo"] == "USD 220.00 (환율 1,336.90 적용)"
        assert "foreign_amount" not in record and "currency" not in record

    def test_rounds_half_up_to_won(self):
        parsed = {**FOREIGN_PARSED, "foreign_amount": Decimal("0.50")}
        with patch(GET_KRW_RATE, return_value=Decimal("1001")):
            # 0.50 * 1001 = 500.5 → 501
            assert convert_foreign_amount(parsed)["amount"] == 501


@pytest.mark.django_db
class TestRecordForeignCardPayment:
    def test_expense_and_notion_get_krw_amount_and_memo(self):
        with (
            patch(GET_KRW_RATE, return_value=Decimal("1336.9")),
            patch(NOTION_CREATE) as mock_create,
        ):
            expense = record_card_payment(dict(FOREIGN_PARSED))

        expense.refresh_from_db()
        assert expense.amount == 294118
        assert expense.memo == "USD 220.00 (환율 1,336.90 적용)"
        notion_record = mock_create.call_args.args[0]
        assert notion_record["amount"] == 294118
        assert notion_record["memo"] == expense.memo

    def test_rate_failure_records_nothing(self):
        with (
            patch(GET_KRW_RATE, side_effect=ExchangeRateError("down")),
            patch(NOTION_CREATE) as mock_create,
        ):
            with pytest.raises(ExchangeRateError):
                record_card_payment(dict(FOREIGN_PARSED))

        mock_create.assert_not_called()
        assert not Expense.objects.exists()
