"""필터를 적용한 지출 queryset을 대분류별·월별로 집계한다.

차트가 현재 페이지(20건)가 아니라 필터에 맞는 전체 지출을 보도록, 목록 API와 같은
queryset을 받아 DB에서 합계를 낸다(행을 파이썬으로 가져오지 않는다).
"""

from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import TruncMonth

from expenses.constants import ExpenseCategoryEnum


def breakdown_expenses(queryset: QuerySet) -> dict:
    # 목록용 정렬이 붙어 있으면 GROUP BY에 정렬 컬럼이 섞이므로 제거한다.
    base = queryset.order_by()

    totals = base.aggregate(total=Sum("amount"), count=Count("id"))

    labels = dict(ExpenseCategoryEnum.choices)
    by_category = [
        {
            "category": row["category"],
            "label": labels.get(row["category"], row["category"]),
            "total": row["total"] or 0,
            "count": row["count"],
        }
        for row in base.values("category")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total", "category")
    ]

    by_month = [
        {
            "month": row["month"].strftime("%Y-%m"),
            "total": row["total"] or 0,
            "count": row["count"],
        }
        for row in base.annotate(month=TruncMonth("spent_at"))
        .values("month")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("month")
    ]

    return {
        "total": totals["total"] or 0,
        "count": totals["count"] or 0,
        "by_category": by_category,
        "by_month": by_month,
    }
