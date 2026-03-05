import django_filters
from django.db.models import Q

from expenses.models import Expense


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
