import django_filters

from expenses.models import Expense


class ExpenseFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category", lookup_expr="exact")
    sub_category = django_filters.CharFilter(
        field_name="sub_category", lookup_expr="exact"
    )

    # 날짜 범위 필터 (선택적으로 활용)
    spent_at_after = django_filters.DateFilter(field_name="spent_at", lookup_expr="gte")
    spent_at_before = django_filters.DateFilter(
        field_name="spent_at", lookup_expr="lte"
    )

    class Meta:
        model = Expense
        fields = ["category", "sub_category"]
