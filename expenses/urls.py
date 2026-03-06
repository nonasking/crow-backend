from django.urls import include, path
from rest_framework.routers import DefaultRouter

from expenses.views.budget_viewset import BudgetViewSet
from expenses.views.expense_viewset import ExpenseViewSet

router = DefaultRouter()

router.register("", ExpenseViewSet)
router.register("budget", BudgetViewSet)

app_name = "expenses"

urlpatterns = [
    path("", include(router.urls)),
]
