"""0005_normalize_sms_items 데이터 마이그레이션 테스트.

pytest-django-migrator 같은 헬퍼 플러그인이 없으므로 Django의
MigrationExecutor 로 직접 0004(백업 테이블 직후) <-> 0005(정규화 적용) 상태를
오가며 forwards/backwards/idempotency/비대상 미변경을 검증한다.

주의:
- 마이그레이션 상태를 바꾸므로 transaction=True 가 필요하다.
- 시드/조회는 반드시 **해당 마이그레이션 상태의 historical 모델**을 사용한다.
  (글로벌 모델은 0006 에서 추가된 auto_classified 컬럼을 포함하므로, 0004/0005
  상태 테이블에 대고 쓰면 'column does not exist' 로 깨진다.)
- teardown 은 다른 테스트를 위해 **최신(0006)** 상태로 복귀시킨다.
"""

import importlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

APP = "expenses"
BEFORE = "0004_expenseitembackup"     # 정규화 적용 전 (백업 테이블만 존재)
AFTER = "0005_normalize_sms_items"    # 정규화 적용 후
LATEST = "0006_expense_auto_classified"  # 스위트 다른 테스트용 최신 상태

# 마이그레이션 대상 / 비대상 시드 데이터
# (item, expected_after_forwards)
SEED = [
    # 변경 대상 (SMS 포맷)
    ("(일시불)06/20 카페63도", "카페63도"),
    ("(일시불)05/31 18:28 홈플러스익스", "홈플러스익스"),
    ("(할부3개월)06/03 20:52 (주)이마트", "이마트"),
    # 비대상: '(' 로 시작하지 않음 → 후보 쿼리에서 제외
    ("식재료", "식재료"),
    ("설명_가맹점", "설명_가맹점"),
    ("잔액 2,311,720원", "잔액 2,311,720원"),
    # 비대상: '(' 로 시작하지만 SMS 포맷 아님 → normalize no-op
    ("(주)이마트", "(주)이마트"),
]


def _migrate_to(target):
    executor = MigrationExecutor(connection)
    executor.migrate([(APP, target)])


def _state_apps(target):
    """target 마이그레이션 상태의 historical apps 레지스트리."""
    executor = MigrationExecutor(connection)
    return executor.loader.project_state((APP, target)).apps


def _model(target, name):
    return _state_apps(target).get_model(APP, name)


def _seed(model):
    created = []
    for item, _ in SEED:
        obj = model.objects.create(
            spent_at="2024-06-20",
            category="ETC",
            sub_category="ETC",
            item=item,
            payment_method="SHINHAN",
            amount=1000,
        )
        created.append(obj.id)
    return created


@pytest.mark.django_db(transaction=True)
class TestNormalizeSmsItemsMigration:

    def setup_method(self, method):
        # 각 테스트는 BEFORE 상태에서 시작
        _migrate_to(BEFORE)

    def teardown_method(self, method):
        # 다른 테스트에 영향 없도록 최신 상태로 복귀 (스키마 복원)
        _migrate_to(LATEST)

    # ── forwards ───────────────────────────────────────────
    def test_forwards_normalizes_only_sms_rows(self):
        ids = _seed(_model(BEFORE, "Expense"))

        _migrate_to(AFTER)

        Expense = _model(AFTER, "Expense")
        for idx, (original, expected) in enumerate(SEED):
            obj = Expense.objects.get(id=ids[idx])
            assert obj.item == expected, (
                f"{original!r} -> {obj.item!r}, expected {expected!r}"
            )

    def test_forwards_backs_up_only_changed_rows(self):
        ids = _seed(_model(BEFORE, "Expense"))

        _migrate_to(AFTER)

        Expense = _model(AFTER, "Expense")
        Backup = _model(AFTER, "ExpenseItemBackup")

        # SEED 중 실제로 바뀌는 행 = 3건
        changed = [s for s in SEED if s[0] != s[1]]
        assert Backup.objects.count() == len(changed)

        # 백업의 original/normalized 정확성
        for backup in Backup.objects.all():
            assert backup.original_item != backup.normalized_item
            exp = Expense.objects.get(id=backup.expense_id)
            assert exp.item == backup.normalized_item

    def test_forwards_does_not_touch_non_candidates(self):
        ids = _seed(_model(BEFORE, "Expense"))

        _migrate_to(AFTER)

        Expense = _model(AFTER, "Expense")
        unchanged = {s[0] for s in SEED if s[0] == s[1]}
        items = set(Expense.objects.filter(id__in=ids).values_list("item", flat=True))
        assert unchanged.issubset(items)

    # ── idempotency ────────────────────────────────────────
    def test_forwards_idempotent(self):
        """0005 forwards 를 직접 한 번 더 호출해도 무변화 + 백업 중복 없음."""
        ids = _seed(_model(BEFORE, "Expense"))

        _migrate_to(AFTER)
        Expense = _model(AFTER, "Expense")
        Backup = _model(AFTER, "ExpenseItemBackup")

        first_items = dict(
            Expense.objects.filter(id__in=ids).values_list("id", "item")
        )
        first_backup_count = Backup.objects.count()

        # 마이그레이션 모듈의 forwards 를 AFTER 상태 apps 로 재호출 (RunPython 2회 모사).
        mig = importlib.import_module(
            "expenses.migrations.0005_normalize_sms_items"
        )
        mig.forwards(_state_apps(AFTER), None)

        second_items = dict(
            Expense.objects.filter(id__in=ids).values_list("id", "item")
        )
        assert first_items == second_items
        # 이미 백업된 expense 는 건너뛰므로 백업 건수도 동일 (중복 백업 없음)
        assert Backup.objects.count() == first_backup_count

    # ── backwards ──────────────────────────────────────────
    def test_backwards_restores_originals(self):
        ids = _seed(_model(BEFORE, "Expense"))

        _migrate_to(AFTER)
        assert _model(AFTER, "ExpenseItemBackup").objects.count() == 3

        # 되돌리기
        _migrate_to(BEFORE)

        Expense = _model(BEFORE, "Expense")
        for idx, (original, _expected) in enumerate(SEED):
            obj = Expense.objects.get(id=ids[idx])
            assert obj.item == original, (
                f"restore failed: got {obj.item!r}, expected {original!r}"
            )
        # 백업은 정리됨
        assert _model(BEFORE, "ExpenseItemBackup").objects.count() == 0
