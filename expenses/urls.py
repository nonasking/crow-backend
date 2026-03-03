from django.urls import include, path
from rest_framework.routers import DefaultRouter

from expenses.views.expense_viewset import ExpenseViewSet

router = DefaultRouter()

router.register("", ExpenseViewSet)

app_name = "expenses"

urlpatterns = [
    path("", include(router.urls)),
]
