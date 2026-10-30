import calendar
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from expenses.constants import LOCAL_TIMEZONE
from expenses.models import Budget, Expense


def summarize_expenses(
    year: int,
    month: int,
    categories: list[str] | None = None,
    spent_at_after: date | None = None,
    spent_at_before: date | None = None,
    today: date | None = None,
) -> dict:
    """지출 합계와 예산(전체/일할)을 집계한다.

    spent_at_after/spent_at_before가 둘 다 있으면 그 기간 기준으로,
    아니면 year/month 한 달 기준으로 집계한다.
    """
    today = today or timezone.localdate(timezone=LOCAL_TIMEZONE)

    budget_qs = Budget.objects.all()
    expense_qs = Expense.objects.all()
    if categories:
        budget_qs = budget_qs.filter(category__in=categories)
        expense_qs = expense_qs.filter(category__in=categories)

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
        for m_year, m_month, covered_days in _months_in_range(
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
            budget_qs.filter(year=year, month=month).aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )
        days_in_month = calendar.monthrange(year, month)[1]
        # 폴백: 오늘까지
        delta_days = today.day
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


def _months_in_range(start: date, end: date) -> list[tuple[int, int, int]]:
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
