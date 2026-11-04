"""GET /expenses/expenses/breakdown/ — 차트용 대분류별·월별 집계."""

import pytest
from rest_framework import status

from expenses.constants import (
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)
from expenses.models import Expense

URL = "/expenses/expenses/breakdown/"


def _expense(spent_at, amount, category=ExpenseCategoryEnum.FOOD, item="식당", **extra):
    sub = {
        ExpenseCategoryEnum.FOOD: ExpenseSubCategoryEnum.BEVERAGE,
        ExpenseCategoryEnum.TRANSPORT: ExpenseSubCategoryEnum.TRANSPORT,
    }[category]
    return Expense.objects.create(
        spent_at=spent_at,
        category=category,
        sub_category=sub,
        item=item,
        payment_method=ExpensePaymentMethodEnum.WOORI,
        amount=amount,
        **extra,
    )


@pytest.mark.django_db
class TestExpenseBreakdown:
    def test_requires_auth(self, client):
        assert client.get(URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty(self, auth_client):
        response = auth_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"total": 0, "count": 0, "by_category": [], "by_month": []}

    def test_aggregates_beyond_one_page(self, auth_client):
        # 목록 페이지(20건)보다 많아도 전부 집계해야 한다.
        for day in range(1, 26):
            _expense(f"2026-03-{day:02d}", 1000)
        for day in range(1, 6):
            _expense(f"2026-04-{day:02d}", 2000, category=ExpenseCategoryEnum.TRANSPORT, item="지하철")

        data = auth_client.get(URL).data

        assert data["total"] == 25 * 1000 + 5 * 2000
        assert data["count"] == 30
        assert data["by_category"] == [
            {"category": "FOOD", "label": "식대", "total": 25000, "count": 25},
            {"category": "TRANSPORT", "label": "교통비", "total": 10000, "count": 5},
        ]
        assert data["by_month"] == [
            {"month": "2026-03", "total": 25000, "count": 25},
            {"month": "2026-04", "total": 10000, "count": 5},
        ]

    def test_applies_same_filters_as_list(self, auth_client):
        _expense("2026-03-10", 1000, item="스타벅스")
        _expense("2026-03-11", 3000, item="스타벅스")
        _expense("2026-04-01", 5000, item="스타벅스")
        _expense("2026-03-12", 7000, category=ExpenseCategoryEnum.TRANSPORT, item="지하철")

        params = {
            "category": "FOOD",
            "spent_at_after": "2026-03-01",
            "spent_at_before": "2026-03-31",
            "search": "스타",
        }
        data = auth_client.get(URL, params).data
        listed = auth_client.get("/expenses/expenses/", params).data

        assert data["total"] == 4000
        assert data["count"] == listed["count"] == 2

    def test_result_does_not_depend_on_pagination_or_ordering_params(self, auth_client):
        # 페이지·정렬 파라미터를 줘도 전체 기준 집계가 그대로 나오는지 본다.
        # (집계 SQL에 정렬 컬럼이 섞이지 않는 것은 서비스의 order_by()가 막는다)
        for day in range(1, 4):
            _expense(f"2026-03-{day:02d}", 1000)

        data = auth_client.get(URL, {"page": 2, "page_size": 1, "ordering": "-amount"}).data

        assert data["count"] == 3
        assert data["by_month"] == [{"month": "2026-03", "total": 3000, "count": 3}]

    def test_negative_amounts_are_netted(self, auth_client):
        _expense("2026-03-01", 10000)
        _expense("2026-03-02", -4000, item="환불")

        data = auth_client.get(URL).data

        assert data["total"] == 6000
        assert data["by_category"][0]["total"] == 6000

    def test_month_and_year_boundaries(self, auth_client):
        for spent_at in ["2025-12-31", "2026-01-01", "2026-03-31", "2026-04-01"]:
            _expense(spent_at, 1000)

        data = auth_client.get(URL).data

        assert [(m["month"], m["count"]) for m in data["by_month"]] == [
            ("2025-12", 1),
            ("2026-01", 1),
            ("2026-03", 1),
            ("2026-04", 1),
        ]

    def test_category_ties_are_ordered_by_value(self, auth_client):
        _expense("2026-03-01", 1000, category=ExpenseCategoryEnum.TRANSPORT)
        _expense("2026-03-01", 1000, category=ExpenseCategoryEnum.FOOD)

        data = auth_client.get(URL).data

        assert [c["category"] for c in data["by_category"]] == ["FOOD", "TRANSPORT"]


@pytest.mark.django_db
def test_breakdown_runs_three_aggregate_queries(django_assert_num_queries):
    from expenses.services.expense_breakdown_service import breakdown_expenses

    for day in range(1, 31):
        _expense(f"2026-03-{day:02d}", 1000)

    # 합계 1번 + 대분류별 1번 + 월별 1번. 행 수와 무관해야 한다.
    with django_assert_num_queries(3):
        breakdown_expenses(Expense.objects.all().order_by("-spent_at"))
