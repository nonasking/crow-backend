from unittest.mock import patch

import pytest
from rest_framework import status

from expenses.constants import (
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
