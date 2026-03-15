import calendar
from datetime import date

from django.db.models import Count, Sum
from rest_framework import serializers

from expenses.models import Budget, Expense
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
        year = self.validated_data["year"]
        month = self.validated_data["month"]
        categories = self.validated_data.get("category")
        spent_at_after = self.validated_data.get("spent_at_after")
        spent_at_before = self.validated_data.get("spent_at_before")

        # 예산 합계
        budget_qs = Budget.objects.filter(year=year, month=month)
        if categories:
            budget_qs = budget_qs.filter(category__in=categories.split(","))
        total_budget = budget_qs.aggregate(total=Sum("amount"))["total"] or 0

        # 일할 예산 계산
        days_in_month = calendar.monthrange(year, month)[1]
        if spent_at_after and spent_at_before:
            # 필터 범위의 일수로 계산
            delta_days = (spent_at_before - spent_at_after).days + 1
        else:
            # 폴백: 오늘까지
            delta_days = date.today().day
        daily_budget = round(total_budget / days_in_month * delta_days)

        # 지출 합계
        expense_qs = Expense.objects.filter(
            spent_at__year=year,
            spent_at__month=month,
        )
        if categories:
            expense_qs = expense_qs.filter(category__in=categories.split(","))
        if spent_at_after:
            expense_qs = expense_qs.filter(spent_at__gte=spent_at_after)
        if spent_at_before:
            expense_qs = expense_qs.filter(spent_at__lte=spent_at_before)

        result = expense_qs.aggregate(total=Sum("amount"), count=Count("id"))

        return {
            "year": year,
            "month": month,
            "total_budget": total_budget,
            "daily_budget": daily_budget,
            "total_spent": result["total"] or 0,
            "count": result["count"] or 0,
        }
