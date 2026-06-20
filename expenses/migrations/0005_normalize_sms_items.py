# Data migration: SMS 포맷 Expense.item 가맹점명 정규화.
#
# - forwards : `(일시불)…` / `(할부…)…` 로 시작하는 SMS 포맷 item에만
#              receivers.services.normalize_merchant 를 적용해 깨끗한 가맹점명으로
#              치환한다. 변경되는 행마다 ExpenseItemBackup 에 원본을 보존한다.
#              매칭되지 않는 PLAIN/OLD/잔액 행은 건드리지 않는다.
# - backwards: ExpenseItemBackup 에 보존된 원본 item 으로 복원하고 백업을 제거한다.
#
# 멱등성: normalize_merchant 는 이미 정규화된(마커 없는) item 에는 매칭되지 않아
#         값을 그대로 반환하므로, 두 번 적용해도 결과가 동일하다. 또한 이미 백업이
#         존재하는 expense 는 재처리에서 제외한다.

from django.db import migrations

# 파서와 동일한 단일 진실 공급원(single source of truth)을 재사용한다.
from receivers.services import normalize_merchant


def forwards(apps, schema_editor):
    Expense = apps.get_model("expenses", "Expense")
    ExpenseItemBackup = apps.get_model("expenses", "ExpenseItemBackup")

    # 이미 백업된(=정규화 처리된) expense 는 건너뛴다 → 멱등성/재실행 안전.
    already_backed_up = set(
        ExpenseItemBackup.objects.values_list("expense_id", flat=True)
    )

    backups = []
    to_update = []

    # SMS 포맷 후보만 좁혀서 조회 (PLAIN/OLD/잔액 행은 조회 대상에서 제외).
    candidates = Expense.objects.filter(item__startswith="(").exclude(
        id__in=already_backed_up
    )

    for expense in candidates.iterator():
        original = expense.item
        normalized = normalize_merchant(original)

        # 실제로 바뀌는 경우(=SMS 포맷에 매칭된 경우)에만 처리한다.
        if normalized == original:
            continue

        backups.append(
            ExpenseItemBackup(
                expense_id=expense.id,
                original_item=original,
                normalized_item=normalized,
            )
        )
        expense.item = normalized
        to_update.append(expense)

    if backups:
        ExpenseItemBackup.objects.bulk_create(backups, batch_size=500)
    if to_update:
        Expense.objects.bulk_update(to_update, ["item"], batch_size=500)


def backwards(apps, schema_editor):
    Expense = apps.get_model("expenses", "Expense")
    ExpenseItemBackup = apps.get_model("expenses", "ExpenseItemBackup")

    to_restore = []
    restored_backup_ids = []
    for backup in ExpenseItemBackup.objects.iterator():
        # 외부에서 그 사이 수정하지 않은(=정규화된 값 그대로인) 행만 안전하게 복원.
        try:
            expense = Expense.objects.get(id=backup.expense_id)
        except Expense.DoesNotExist:
            continue
        if expense.item == backup.normalized_item:
            expense.item = backup.original_item
            to_restore.append(expense)
            restored_backup_ids.append(backup.id)

    if to_restore:
        Expense.objects.bulk_update(to_restore, ["item"], batch_size=500)

    # 복원에 성공한 백업만 정리한다. 외부에서 수정됐거나 expense 가 삭제돼
    # 복원하지 못한 행의 백업은 원본 보존을 위해 남겨 둔다 (영구 소실 방지).
    if restored_backup_ids:
        ExpenseItemBackup.objects.filter(id__in=restored_backup_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0004_expenseitembackup"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
