from django.db import models


class ExpenseItemBackup(models.Model):
    """SMS 가맹점명 정규화 데이터 마이그레이션의 원본 item 백업.

    `Expense.item`을 정규화하기 전 원본 문자열을 보존하여
    reverse migration(되돌리기) 시 원래 값으로 복원할 수 있게 한다.
    memo는 절대 건드리지 않는다.
    """

    expense = models.ForeignKey(
        "expenses.Expense",
        on_delete=models.CASCADE,
        related_name="item_backups",
        verbose_name="지출",
    )
    original_item = models.CharField(max_length=100, verbose_name="원본 항목")
    normalized_item = models.CharField(max_length=100, verbose_name="정규화 항목")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expense_item_backup"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.expense_id} {self.original_item!r} -> {self.normalized_item!r}"
