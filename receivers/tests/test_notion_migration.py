from datetime import date
from unittest.mock import patch

import pytest

from expenses.constants import (
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)
from expenses.models import Budget, Expense
from receivers.externals.notion.api_client import NotionClient


def _select(name):
    return {"select": {"name": name}}


def _expense_page(page_id, spent_at, item, amount):
    return {
        "id": page_id,
        "properties": {
            "항목": {"title": [{"text": {"content": item}}]},
            "날짜": {"date": {"start": spent_at}},
            "지출": {"number": amount},
            "대분류": _select(ExpenseCategoryEnum.FOOD.label),
            "소분류": _select(ExpenseSubCategoryEnum.DINING_OUT.label),
            "결제방식": _select(ExpensePaymentMethodEnum.SHINHAN.label),
            "비고": {"rich_text": []},
        },
    }


def _budget_page(page_id, year, month, amount):
    return {
        "id": page_id,
        "properties": {
            "연도": {"number": year},
            "월": {"number": month},
            "대분류": _select(ExpenseCategoryEnum.FOOD.label),
            "소분류": _select(ExpenseSubCategoryEnum.DINING_OUT.label),
            "예산": {"number": amount},
        },
    }


def _migrate_expense(pages, **kwargs):
    with patch.object(NotionClient, "_fetch_all_pages", return_value=pages):
        return NotionClient(token="t", version="v").migrate_expense_to_db(**kwargs)


def _migrate_budget(pages, **kwargs):
    with patch.object(NotionClient, "_fetch_all_pages", return_value=pages):
        return NotionClient(token="t", version="v").migrate_budget_to_db(**kwargs)


@pytest.mark.django_db
class TestMigrateExpenseToDb:
    def test_skip_duplicates_matches_spent_at_item_amount(self):
        Expense.objects.create(
            spent_at=date(2026, 3, 1),
            item="김밥천국",
            amount=8000,
            payment_method=ExpensePaymentMethodEnum.SHINHAN,
        )
        pages = [
            _expense_page("dup", "2026-03-01", "김밥천국", 8000),
            # Notion number가 float로 와도 같은 금액이면 중복으로 본다
            _expense_page("dup-float", "2026-03-01", "김밥천국", 8000.0),
            _expense_page("other-day", "2026-03-02", "김밥천국", 8000),
            _expense_page("no-date", "", "날짜없음", 1000),
        ]

        result = _migrate_expense(pages, skip_duplicates=True)

        assert result == {
            "total": 4,
            "created": 1,
            "skipped": 3,
            "errors": ["no-date"],
        }
        assert Expense.objects.count() == 2

    def test_without_skip_duplicates_creates_all(self):
        Expense.objects.create(
            spent_at=date(2026, 3, 1),
            item="김밥천국",
            amount=8000,
            payment_method=ExpensePaymentMethodEnum.SHINHAN,
        )
        pages = [_expense_page("dup", "2026-03-01", "김밥천국", 8000)]

        result = _migrate_expense(pages, skip_duplicates=False)

        assert result["created"] == 1
        assert Expense.objects.count() == 2

    def test_batches_bulk_create(self):
        pages = [
            _expense_page(f"p{i}", "2026-03-01", f"가맹점{i}", 1000) for i in range(5)
        ]

        result = _migrate_expense(pages, batch_size=2)

        assert result["created"] == 5
        assert Expense.objects.count() == 5


@pytest.mark.django_db
class TestMigrateBudgetToDb:
    def test_skip_duplicates_by_year_month_category(self):
        Budget.objects.create(
            year=2026,
            month=3,
            category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.DINING_OUT,
            amount=300000,
        )
        pages = [
            _budget_page("dup", 2026, 3, 500000),
            _budget_page("next-month", 2026, 4, 500000),
            _budget_page("bad-month", 2026, 13, 500000),
        ]

        result = _migrate_budget(pages)

        assert result == {
            "total": 3,
            "created": 1,
            "skipped": 2,
            "errors": ["bad-month"],
        }
        assert Budget.objects.count() == 2
