import django_filters
from django.db.models import Q
from rest_framework.filters import OrderingFilter

from expenses.models import Budget, Expense


class ExpenseFilter(django_filters.FilterSet):
    category = django_filters.BaseInFilter(field_name="category", lookup_expr="in")
    sub_category = django_filters.BaseInFilter(
        field_name="sub_category", lookup_expr="in"
    )
    payment_method = django_filters.BaseInFilter(
        field_name="payment_method", lookup_expr="in"
    )

    # 날짜 범위
    spent_at_after = django_filters.DateFilter(field_name="spent_at", lookup_expr="gte")
    spent_at_before = django_filters.DateFilter(
        field_name="spent_at", lookup_expr="lte"
    )

    # 금액 범위
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    # 텍스트 검색
    search = django_filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(item__icontains=value) | Q(memo__icontains=value))

    class Meta:
        model = Expense
        fields = [
            "category",
            "sub_category",
            "payment_method",
            "spent_at_after",
            "spent_at_before",
            "amount_min",
            "amount_max",
            "search",
        ]


class BudgetFilter(django_filters.FilterSet):
    category = django_filters.BaseInFilter(field_name="category", lookup_expr="in")
    sub_category = django_filters.BaseInFilter(
        field_name="sub_category", lookup_expr="in"
    )

    year = django_filters.NumberFilter(field_name="year", lookup_expr="exact")
    month = django_filters.NumberFilter(field_name="month", lookup_expr="exact")

    class Meta:
        model = Budget
        fields = [
            "category",
            "sub_category",
            "year",
            "month",
        ]


class StableOrderingFilter(OrderingFilter):
    """정렬 기준이 같은 행이 많아도(비고는 대부분 빈 값) 순서가 고정되도록 마지막에 -id를 붙인다.

    동점 행의 순서가 쿼리마다 달라지면 페이지를 넘길 때 행이 중복되거나 빠진다.
    """

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering
        ordering = list(ordering)
        if not any(field.lstrip("-") in ("id", "pk") for field in ordering):
            ordering.append("-id")
        return ordering
