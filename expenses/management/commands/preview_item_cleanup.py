"""SMS 가맹점명 정규화 데이터 마이그레이션의 영향 범위를 미리 확인하는 명령.

데이터 마이그레이션(0005_normalize_sms_items)과 **동일한** normalize_merchant 를
사용하여, 실제 변경 없이 몇 건이 어떻게 바뀌는지(before -> after) 보여준다.

사용법:
    # 영향 건수 + 변경 샘플(기본 20건) 출력 (읽기 전용, DB 미변경)
    poetry run python manage.py preview_item_cleanup

    # 샘플 개수 조정
    poetry run python manage.py preview_item_cleanup --limit 50

    # 모든 변경 대상 출력
    poetry run python manage.py preview_item_cleanup --all
"""

from django.core.management.base import BaseCommand

from expenses.models import Expense
from receivers.services import normalize_merchant


class Command(BaseCommand):
    help = "SMS 포맷 Expense.item 정규화의 영향 건수/샘플을 미리 확인합니다 (DB 미변경)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="출력할 변경 샘플 개수 (기본 20).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="변경 대상 전체를 출력합니다 (--limit 무시).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        show_all = options["all"]

        candidates = Expense.objects.filter(item__startswith="(").order_by("id")

        changes = []
        for expense in candidates.iterator():
            original = expense.item
            normalized = normalize_merchant(original)
            if normalized != original:
                changes.append((expense.id, original, normalized))

        total_scanned = candidates.count()
        total_changed = len(changes)

        self.stdout.write(self.style.MIGRATE_HEADING("=== SMS item 정규화 미리보기 (DRY-RUN) ==="))
        self.stdout.write(f"SMS 포맷 후보(item이 '('로 시작): {total_scanned}건")
        self.stdout.write(
            self.style.SUCCESS(f"실제 변경 대상: {total_changed}건")
        )
        self.stdout.write(
            f"미변경(이미 정규화됨/비매칭): {total_scanned - total_changed}건"
        )

        if not changes:
            self.stdout.write(self.style.WARNING("변경할 항목이 없습니다."))
            return

        sample = changes if show_all else changes[:limit]
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"--- 변경 샘플 ({len(sample)}/{total_changed}건) ---"))
        for expense_id, original, normalized in sample:
            self.stdout.write(f"#{expense_id}: {original!r}  ->  {normalized!r}")

        if not show_all and total_changed > len(sample):
            self.stdout.write(
                self.style.NOTICE(
                    f"... 외 {total_changed - len(sample)}건. 전체는 --all 로 확인하세요."
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "이 명령은 DB를 변경하지 않습니다. "
                "실제 적용은 `migrate expenses 0005_normalize_sms_items` 로 수행하세요."
            )
        )
