from unittest.mock import patch

import pytest
from rest_framework import status

from expenses.constants import ExpenseCategoryEnum, ExpensePaymentMethodEnum


@pytest.mark.django_db
def test_create_expense(client):

    url = "/expenses/"
    payload = {
        "spent_at": "2024-05-20",
        "category": ExpenseCategoryEnum.PHONE_BILL,
        "sub_category": ExpenseCategoryEnum.PHONE_BILL,
        "item": "5월 통신비",
        "payment_method": ExpensePaymentMethodEnum.WOORI,
        "amount": 45000,
        "memo": "메모메모",
    }
    response = client.post(url, data=payload, content_type="application/json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["category"] == payload["category"]


@pytest.mark.django_db
@patch("receivers.externals.notion.api_client.NotionClient.migrate_to_db")
def test_migrate_notion_data_to_expense(mock_migrate, client):
    migrate_result = {"total": 3, "created": 2, "skipped": 1, "errors": []}
    mock_migrate.return_value = migrate_result
    url = "/expenses/migrate-from-notion/"
    response = client.post(url, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total"] == migrate_result["total"]
    assert response.data["created"] == migrate_result["created"]
    assert response.data["skipped"] == migrate_result["skipped"]
    assert response.data["errors"] == migrate_result["errors"]
