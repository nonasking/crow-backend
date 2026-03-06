from datetime import date

from django.db.models import Sum
from rest_framework import serializers

from expenses.models import Budget
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


class BudgetSummarySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)
    month = serializers.IntegerField(required=False)
    category = serializers.CharField(required=False)

    def validate(self, attrs):
        today = date.today()

        attrs["year"] = attrs.get("year", today.year)
        attrs["month"] = attrs.get("month", today.month)

        return attrs

    def summary(self):
        year = self.validated_data["year"]
        month = self.validated_data["month"]
        categories = self.validated_data.get("category")

        qs = Budget.objects.filter(year=year, month=month)

        if categories:
            qs = qs.filter(category__in=categories.split(","))

        total_budget = qs.aggregate(total=Sum("amount"))["total"] or 0

        return {
            "year": year,
            "month": month,
            "total_budget": total_budget,
        }
