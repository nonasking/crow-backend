from django.db import models

from expenses.constants import (
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)


class Expense(models.Model):

    spent_at = models.DateField(verbose_name="날짜")
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategoryEnum.choices,
        default=ExpenseCategoryEnum.ETC,
        verbose_name="대분류",
    )
    sub_category = models.CharField(
        max_length=20,
        choices=ExpenseSubCategoryEnum.choices,
        default=ExpenseSubCategoryEnum.ETC,
        verbose_name="소분류",
    )
    item = models.CharField(max_length=100, verbose_name="항목")
    payment_method = models.CharField(
        max_length=20,
        choices=ExpensePaymentMethodEnum.choices,
        verbose_name="결제방식",
    )
    amount = models.IntegerField(verbose_name="지출")
    memo = models.TextField(blank=True, default="", verbose_name="비고")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expense"
        ordering = ["-spent_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "spent_at"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return f"[{self.spent_at}] {self.item} {self.amount:,}원"
