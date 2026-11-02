from django.utils import timezone
from rest_framework import serializers

from expenses.constants import LOCAL_TIMEZONE
from expenses.services.expense_summary_service import summarize_expenses
from receivers.externals.notion.api_client import NotionClient


class NotionExpenseMigrateSerializer(serializers.Serializer):
    skip_duplicates = serializers.BooleanField(default=False)

    def save(self):
        skip_duplicates = self.validated_data["skip_duplicates"]
        return NotionClient().migrate_expense_to_db(skip_duplicates=skip_duplicates)


class NotionBudgetMigrateSerializer(serializers.Serializer):
    # Budget은 (year, month, category, sub_category) unique 제약이 있어서
    # 중복을 건너뛰지 않으면 두 번째 실행부터 제약 위반이 난다.
    skip_duplicates = serializers.BooleanField(default=True)

    def save(self):
        skip_duplicates = self.validated_data["skip_duplicates"]
        return NotionClient().migrate_budget_to_db(skip_duplicates=skip_duplicates)


class ExpenseSummarySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    category = serializers.CharField(required=False)
    spent_at_after = serializers.DateField(required=False)
    spent_at_before = serializers.DateField(required=False)

    def validate(self, attrs):
        today = timezone.localdate(timezone=LOCAL_TIMEZONE)
        attrs["year"] = attrs.get("year", today.year)
        attrs["month"] = attrs.get("month", today.month)
        return attrs

    def summary(self):
        data = self.validated_data
        categories = data.get("category")
        return summarize_expenses(
            year=data["year"],
            month=data["month"],
            categories=categories.split(",") if categories else None,
            spent_at_after=data.get("spent_at_after"),
            spent_at_before=data.get("spent_at_before"),
        )
