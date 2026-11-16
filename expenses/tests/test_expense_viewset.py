from unittest.mock import patch

import pytest
from rest_framework import status

from expenses.constants import (
    CATEGORY_SUBCATEGORY_MAP,
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)
from expenses.models.expense import Expense


@pytest.mark.django_db
def test_create_expense(auth_client):

    url = "/expenses/expenses/"
    payload = {
        "spent_at": "2024-05-20",
        "category": ExpenseCategoryEnum.PHONE_BILL,
        "sub_category": ExpenseCategoryEnum.PHONE_BILL,
        "item": "5월 통신비",
        "payment_method": ExpensePaymentMethodEnum.WOORI,
        "amount": 45000,
        "memo": "메모메모",
    }
    response = auth_client.post(url, data=payload, content_type="application/json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["category"] == payload["category"]


@pytest.mark.django_db
def test_list_expense(auth_client):
    Expense.objects.create(
        amount=1,
        spent_at="2024-01-01",
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )
    Expense.objects.create(
        amount=1,
        spent_at="2024-01-02",
        category=ExpenseCategoryEnum.ALLOWANCE,
        sub_category=ExpenseSubCategoryEnum.ALLOWANCE_MS,
    )
    Expense.objects.create(
        amount=1,
        spent_at="2024-01-03",
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )

    url = "/expenses/expenses/"
    response = auth_client.get(f"{url}?category=UNSETTLED&sub_category=UNSETTLED")
    assert response.status_code == status.HTTP_200_OK
    assert response.data.get("count") == 2


@pytest.mark.django_db
def test_auto_classified_is_read_only_on_create(auth_client):
    # PATCH/POST 로 auto_classified 를 못 바꾼다 (read_only_fields).
    url = "/expenses/expenses/"
    payload = {
        "spent_at": "2024-05-20",
        "category": ExpenseCategoryEnum.PHONE_BILL,
        "sub_category": ExpenseSubCategoryEnum.PHONE_BILL,
        "item": "통신비",
        "payment_method": ExpensePaymentMethodEnum.WOORI,
        "amount": 45000,
        "auto_classified": True,  # 무시되어야 함
    }
    response = auth_client.post(url, data=payload, content_type="application/json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["auto_classified"] is False
    created = Expense.objects.get(id=response.data["id"])
    assert created.auto_classified is False


@pytest.mark.django_db
@patch("receivers.externals.notion.api_client.NotionClient.migrate_expense_to_db")
def test_migrate_notion_data_to_expense(mock_migrate, auth_client):
    migrate_result = {"total": 3, "created": 2, "skipped": 1, "errors": []}
    mock_migrate.return_value = migrate_result
    url = "/expenses/expenses/migrate-expenses-from-notion/"
    response = auth_client.post(url, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total"] == migrate_result["total"]
    assert response.data["created"] == migrate_result["created"]
    assert response.data["skipped"] == migrate_result["skipped"]
    assert response.data["errors"] == migrate_result["errors"]


@pytest.mark.django_db
def test_summary_spans_multiple_months(auth_client):
    from expenses.models import Budget

    for spent_at, amount in [
        ("2024-12-31", 999),  # 기간 밖
        ("2025-01-01", 100),
        ("2025-06-15", 200),
        ("2026-08-15", 300),
        ("2026-08-16", 999),  # 기간 밖
    ]:
        Expense.objects.create(
            amount=amount,
            spent_at=spent_at,
            category=ExpenseCategoryEnum.UNSETTLED,
            sub_category=ExpenseSubCategoryEnum.UNSETTLED,
        )
    Budget.objects.create(year=2025, month=1, amount=31000)
    Budget.objects.create(year=2026, month=8, amount=31000)
    Budget.objects.create(year=2026, month=9, amount=99999)  # 기간 밖

    response = auth_client.get(
        "/expenses/expenses/summary/"
        "?year=2025&month=1&spent_at_after=2025-01-01&spent_at_before=2026-08-15"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_spent"] == 600
    assert response.data["count"] == 3
    assert response.data["total_budget"] == 62000
    # 2025-01 전체(31000) + 2026-08의 15일치(15000)
    assert response.data["daily_budget"] == 46000


@pytest.mark.django_db
def test_summary_single_month_range_is_prorated(auth_client):
    from expenses.models import Budget

    Budget.objects.create(year=2026, month=3, amount=31000)

    response = auth_client.get(
        "/expenses/expenses/summary/"
        "?year=2026&month=3&spent_at_after=2026-03-01&spent_at_before=2026-03-10"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_budget"] == 31000
    assert response.data["daily_budget"] == 10000


@pytest.mark.django_db
def test_summary_filters_by_sub_category(auth_client):
    """대분류와 소분류를 함께 고르면 예산·지출 모두 소분류 기준으로 센다."""
    from expenses.models import Budget

    allowance = ExpenseCategoryEnum.ALLOWANCE
    for sub, amount in [
        (ExpenseSubCategoryEnum.ALLOWANCE_MS, 100),
        (ExpenseSubCategoryEnum.ALLOWANCE_MK, 999),
    ]:
        Expense.objects.create(
            amount=amount, spent_at="2026-03-05", category=allowance, sub_category=sub
        )
    Budget.objects.create(
        year=2026, month=3, category=allowance,
        sub_category=ExpenseSubCategoryEnum.ALLOWANCE_MS, amount=31000,
    )
    Budget.objects.create(
        year=2026, month=3, category=allowance,
        sub_category=ExpenseSubCategoryEnum.ALLOWANCE_MK, amount=62000,
    )

    response = auth_client.get(
        "/expenses/expenses/summary/"
        "?year=2026&month=3&spent_at_after=2026-03-01&spent_at_before=2026-03-31"
        f"&category={allowance}&sub_category={ExpenseSubCategoryEnum.ALLOWANCE_MS}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_budget"] == 31000
    assert response.data["daily_budget"] == 31000
    assert response.data["total_spent"] == 100
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_manual_category_edit_clears_auto_classified(auth_client):
    expense = Expense.objects.create(
        spent_at="2024-05-20",
        category=ExpenseCategoryEnum.PHONE_BILL,
        sub_category=ExpenseSubCategoryEnum.PHONE_BILL,
        item="통신비",
        payment_method=ExpensePaymentMethodEnum.WOORI,
        amount=45000,
        auto_classified=True,
    )
    other = next(
        (c, s)
        for c, subs in CATEGORY_SUBCATEGORY_MAP.items()
        for s in subs
        if c != ExpenseCategoryEnum.PHONE_BILL
    )

    response = auth_client.patch(
        f"/expenses/expenses/{expense.id}/",
        data={"category": other[0], "sub_category": other[1]},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    expense.refresh_from_db()
    assert expense.auto_classified is False


@pytest.mark.django_db
def test_memo_edit_keeps_auto_classified(auth_client):
    expense = Expense.objects.create(
        spent_at="2024-05-20",
        category=ExpenseCategoryEnum.PHONE_BILL,
        sub_category=ExpenseSubCategoryEnum.PHONE_BILL,
        item="통신비",
        payment_method=ExpensePaymentMethodEnum.WOORI,
        amount=45000,
        auto_classified=True,
    )

    response = auth_client.patch(
        f"/expenses/expenses/{expense.id}/",
        data={"memo": "메모만 수정"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    expense.refresh_from_db()
    assert expense.auto_classified is True


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["item", "memo"])
def test_ordering_by_item_and_memo(auth_client, field):
    for value in ["나", "가", "다"]:
        Expense.objects.create(
            spent_at="2024-05-20",
            category=ExpenseCategoryEnum.PHONE_BILL,
            sub_category=ExpenseSubCategoryEnum.PHONE_BILL,
            item=value,
            memo=value,
            payment_method=ExpensePaymentMethodEnum.WOORI,
            amount=1000,
        )

    response = auth_client.get(f"/expenses/expenses/?ordering={field}")

    assert response.status_code == status.HTTP_200_OK
    assert [row[field] for row in response.data["results"]] == ["가", "나", "다"]



@pytest.mark.django_db
def test_ordering_ties_are_broken_by_id(auth_client):
    ids = [
        Expense.objects.create(
            spent_at="2024-05-20",
            category=ExpenseCategoryEnum.PHONE_BILL,
            sub_category=ExpenseSubCategoryEnum.PHONE_BILL,
            item="같은 항목",
            memo="",
            payment_method=ExpensePaymentMethodEnum.WOORI,
            amount=1000,
        ).id
        for _ in range(3)
    ]

    response = auth_client.get("/expenses/expenses/?ordering=memo")

    assert [row["id"] for row in response.data["results"]] == sorted(ids, reverse=True)
