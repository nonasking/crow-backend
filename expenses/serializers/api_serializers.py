from datetime import date

from rest_framework import serializers

from expenses.services.expense_summary_service import summarize_expenses
from receivers.externals.notion.api_client import NotionClient


class NotionExpenseMigrateSerializer(serializers.Serializer):
    skip_duplicates = serializers.BooleanField(default=False)

    def save(self):
        skip_duplicates = self.validated_data["skip_duplicates"]
        return NotionClient().migrate_expense_to_db(skip_duplicates=skip_duplicates)


class NotionBudgetMigrateSerializer(serializers.Serializer):
    skip_duplicates = serializers.BooleanField(default=False)

    def save(self):
        skip_duplicates = self.validated_data["skip_duplicates"]
        return NotionClient().migrate_budget_to_db(skip_duplicates=skip_duplicates)


class ExpenseSummarySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)
    month = serializers.IntegerField(required=False)
    category = serializers.CharField(required=False)
    spent_at_after = serializers.DateField(required=False)
    spent_at_before = serializers.DateField(required=False)

    def validate(self, attrs):
        today = date.today()
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
