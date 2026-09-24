import calendar
from datetime import date, timedelta

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

        budget_qs = Budget.objects.all()
        expense_qs = Expense.objects.all()
        if categories:
            budget_qs = budget_qs.filter(category__in=categories.split(","))
            expense_qs = expense_qs.filter(category__in=categories.split(","))

        if spent_at_after and spent_at_before:
            # 기간이 여러 달에 걸칠 수 있으므로 달마다 겹치는 일수만큼 예산을 일할한다
            budget_by_month = {
                (row["year"], row["month"]): row["total"]
                for row in budget_qs.filter(
                    year__gte=spent_at_after.year, year__lte=spent_at_before.year
                )
                .order_by()
                .values("year", "month")
                .annotate(total=Sum("amount"))
            }
            total_budget = 0
            prorated_budget = 0
            for m_year, m_month, covered_days in self._months_in_range(
                spent_at_after, spent_at_before
            ):
                month_budget = budget_by_month.get((m_year, m_month), 0)
                days_in_month = calendar.monthrange(m_year, m_month)[1]
                total_budget += month_budget
                prorated_budget += month_budget / days_in_month * covered_days
            daily_budget = round(prorated_budget)

            expense_qs = expense_qs.filter(
                spent_at__gte=spent_at_after, spent_at__lte=spent_at_before
            )
        else:
            # 기간이 한쪽만 있거나 없으면 year/month 기준 한 달
            total_budget = (
                budget_qs.filter(year=year, month=month).aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )
            days_in_month = calendar.monthrange(year, month)[1]
            # 폴백: 오늘까지
            delta_days = date.today().day
            daily_budget = round(total_budget / days_in_month * delta_days)

            expense_qs = expense_qs.filter(
                spent_at__year=year,
                spent_at__month=month,
            )
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

    @staticmethod
    def _months_in_range(start, end):
        """start~end(양끝 포함)가 걸친 (연, 월, 겹치는 일수) 목록"""
        months = []
        cursor = start
        while cursor <= end:
            days_in_month = calendar.monthrange(cursor.year, cursor.month)[1]
            month_end = cursor.replace(day=days_in_month)
            covered_until = min(month_end, end)
            months.append((cursor.year, cursor.month, (covered_until - cursor).days + 1))
            cursor = month_end + timedelta(days=1)
        return months
