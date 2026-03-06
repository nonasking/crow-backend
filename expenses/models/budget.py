from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from expenses.constants import (
    DEFAULT_EXPENSE_CATEGORY,
    DEFAULT_EXPENSE_SUBCATEGORY,
    ExpenseCategoryEnum,
    ExpenseSubCategoryEnum,
)


class Budget(models.Model):

    year = models.PositiveSmallIntegerField(verbose_name="연도")
    month = models.PositiveSmallIntegerField(
        verbose_name="월", validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategoryEnum.choices,
        default=DEFAULT_EXPENSE_CATEGORY,
        verbose_name="대분류",
    )
    sub_category = models.CharField(
        max_length=20,
        choices=ExpenseSubCategoryEnum.choices,
        default=DEFAULT_EXPENSE_SUBCATEGORY,
        verbose_name="소분류",
    )
    amount = models.IntegerField(verbose_name="예산")
    memo = models.TextField(blank=True, default="", verbose_name="비고")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budget"
        ordering = ["-year", "-month", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "month", "category", "sub_category"],
                name="unique_budget_per_month",
            )
        ]

    def __str__(self):
        return f"[{self.year}-{self.month:02d}] {self.get_category_display()} / {self.get_sub_category_display()} {self.amount:,}"
