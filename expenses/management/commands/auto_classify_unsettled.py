"""UNSETTLED Expense를 결정성 기반 규칙으로 자동분류하는 관리 커맨드.

과거 수동 확정분 이력에서 가맹점별로 결정적인 (category, sub_category)를 학습하여
UNSETTLED 행에 채운다. 모호하거나 신규인 가맹점은 손대지 않고 UNSETTLED로 남긴다.

학습 로직/규칙 채택 기준은 expenses.services.auto_classify_service 에 있다.
(normalize_merchant 는 receivers.services 재사용 — 재구현 금지.)

사용법:
    # dry-run (기본): 매칭 건수/샘플/미매칭 상위 항목 리포트, DB 미변경
    poetry run python manage.py auto_classify_unsettled

    # 임계값 조정
    poetry run python manage.py auto_classify_unsettled --min-count 3

    # 샘플 개수 조정
    poetry run python manage.py auto_classify_unsettled --limit 50

    # 실제 적용 (UNSETTLED 매칭분만 분류 + auto_classified=True)
    poetry run python manage.py auto_classify_unsettled --apply

    # 자동분류분 전체 복원 (UNSETTLED/UNSETTLED, 플래그 해제). 수동분은 미변경.
    poetry run python manage.py auto_classify_unsettled --revert
"""

from django.core.management.base import BaseCommand

from expenses.services.auto_classify_service import (
    classify_unsettled,
    revert_auto_classified,
)


class Command(BaseCommand):
    help = (
        "UNSETTLED Expense를 수동 이력 기반 결정성 규칙으로 자동분류합니다 "
        "(기본 dry-run, DB 미변경)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-count",
            type=int,
            default=2,
            help="규칙 채택 최소 등장 횟수 (기본 2).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="매칭된 UNSETTLED를 실제로 분류 적용합니다 (없으면 dry-run).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="출력할 샘플 개수 (기본 20).",
        )
        parser.add_argument(
            "--revert",
            action="store_true",
            help="auto_classified=True 행을 UNSETTLED로 복원하고 플래그를 해제합니다.",
        )

    def handle(self, *args, **options):
        if options["revert"]:
            self._handle_revert()
            return

        min_count = options["min_count"]
        apply = options["apply"]
        limit = options["limit"]

        report = classify_unsettled(min_count=min_count, apply=apply)

        mode = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"=== UNSETTLED 자동분류 ({mode}, min-count={min_count}) ==="
            )
        )
        self.stdout.write(f"학습된 결정성 규칙: {report['rules_count']}개")
        self.stdout.write(f"UNSETTLED 전체: {report['total_unsettled']}건")
        self.stdout.write(
            self.style.SUCCESS(
                f"매칭(자동분류 대상): {report['matched_count']}건"
            )
        )
        self.stdout.write(
            f"미매칭(UNSETTLED 유지): {report['unmatched_count']}건"
        )

        self._print_matched_samples(report["matched"], limit)
        self._print_unmatched(report["ambiguous"], report["new"], limit)

        self.stdout.write("")
        if apply:
            self.stdout.write(
                self.style.SUCCESS(
                    f"적용 완료: {report['applied']}건을 분류하고 "
                    f"auto_classified=True 로 표시했습니다."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN: DB를 변경하지 않았습니다. "
                    "실제 적용은 --apply 로 수행하세요."
                )
            )

    def _print_matched_samples(self, matched, limit):
        if not matched:
            self.stdout.write(self.style.WARNING("매칭된 항목이 없습니다."))
            return

        sample = matched[:limit]
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"--- 자동분류 샘플 ({len(sample)}/{len(matched)}건) ---"
            )
        )
        for row in sample:
            self.stdout.write(
                f"#{row['id']}: {row['item']!r}  ->  "
                f"{row['category']}/{row['sub_category']}"
            )
        if len(matched) > len(sample):
            self.stdout.write(
                self.style.NOTICE(
                    f"... 외 {len(matched) - len(sample)}건. "
                    f"전체는 --limit 로 조정하세요."
                )
            )

    def _print_unmatched(self, ambiguous, new, limit):
        if ambiguous:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"--- 미매칭(모호: 이력은 있으나 결정적 아님) 상위 {limit} ---"
                )
            )
            for key, count in ambiguous.most_common(limit):
                self.stdout.write(f"  {key!r}: {count}건")

        if new:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"--- 미매칭(신규: 수동 이력 없음) 상위 {limit} ---"
                )
            )
            for key, count in new.most_common(limit):
                self.stdout.write(f"  {key!r}: {count}건")

    def _handle_revert(self):
        self.stdout.write(
            self.style.MIGRATE_HEADING("=== 자동분류 복원 (REVERT) ===")
        )
        reverted = revert_auto_classified()
        self.stdout.write(
            self.style.SUCCESS(
                f"복원 완료: {reverted}건을 UNSETTLED로 되돌리고 "
                f"auto_classified=False 로 해제했습니다. (수동분 미변경)"
            )
        )
