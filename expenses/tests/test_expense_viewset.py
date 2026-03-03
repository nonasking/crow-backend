from unittest.mock import patch

import pytest
from rest_framework import status

from expenses.constants import ExpenseCategoryEnum, ExpensePaymentMethodEnum
from expenses.models import Expense


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
