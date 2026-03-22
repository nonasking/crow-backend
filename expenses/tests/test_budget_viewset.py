import pytest
from rest_framework import status

from expenses.constants import ExpenseCategoryEnum, ExpenseSubCategoryEnum
from expenses.models import Budget


@pytest.mark.django_db
def test_list_budget(auth_client):
    Budget.objects.create(
        amount=1,
        year=2024,
        month=1,
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )
    Budget.objects.create(
        amount=1,
        year=2024,
        month=2,
        category=ExpenseCategoryEnum.ALLOWANCE,
        sub_category=ExpenseSubCategoryEnum.ALLOWANCE_MS,
    )
    Budget.objects.create(
        amount=1,
        year=2024,
        month=3,
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )

    url = "/expenses/budget/"
    response = auth_client.get(f"{url}?category=UNSETTLED&sub_category=UNSETTLED")
    assert response.status_code == status.HTTP_200_OK
    assert response.data.get("count") == 2
