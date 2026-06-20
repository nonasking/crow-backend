"""0005_normalize_sms_items 데이터 마이그레이션 테스트.

pytest-django-migrator 같은 헬퍼 플러그인이 없으므로 Django의
MigrationExecutor 로 직접 0004(백업 테이블 직후) <-> 0005(정규화 적용) 상태를
오가며 forwards/backwards/idempotency/비대상 미변경을 검증한다.

주의: 마이그레이션 상태를 바꾸므로 transaction=True 가 필요하다.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

APP = "expenses"
BEFORE = "0004_expenseitembackup"   # 정규화 적용 전 (백업 테이블만 존재)
AFTER = "0005_normalize_sms_items"  # 정규화 적용 후

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
    # 새 상태 모델 그래프 갱신
    executor.loader.build_graph()


def _seed_expenses(apps_state_model_getter):
    Expense = apps_state_model_getter("Expense")
    created = []
    for item, _ in SEED:
        obj = Expense.objects.create(
            spent_at="2024-06-20",
            category="ETC",
            sub_category="ETC",
            item=item,
            payment_method="SHINHAN",
            amount=1000,
        )
        created.append(obj.id)
    return created


@pytest.fixture
def historical_model():
    """현재(=최신) 상태의 Expense/ExpenseItemBackup 모델 getter."""
    from django.apps import apps

    def _get(name):
        return apps.get_model(APP, name)

    return _get


@pytest.mark.django_db(transaction=True)
class TestNormalizeSmsItemsMigration:

    def setup_method(self, method):
        # 각 테스트는 BEFORE 상태에서 시작
        _migrate_to(BEFORE)

    def teardown_method(self, method):
        # 다른 테스트에 영향 없도록 최신 상태로 복귀
        _migrate_to(AFTER)

    # ── forwards ───────────────────────────────────────────
    def test_forwards_normalizes_only_sms_rows(self, historical_model):
        Expense = historical_model("Expense")
        ids = _seed_expenses(historical_model)

        _migrate_to(AFTER)

        for idx, (original, expected) in enumerate(SEED):
            obj = Expense.objects.get(id=ids[idx])
            assert obj.item == expected, (
                f"{original!r} -> {obj.item!r}, expected {expected!r}"
            )

    def test_forwards_backs_up_only_changed_rows(self, historical_model):
        Expense = historical_model("Expense")
        Backup = historical_model("ExpenseItemBackup")
        ids = _seed_expenses(historical_model)

        _migrate_to(AFTER)

        # SEED 중 실제로 바뀌는 행 = 3건
        changed = [s for s in SEED if s[0] != s[1]]
        assert Backup.objects.count() == len(changed)

        # 백업의 original/normalized 정확성
        for backup in Backup.objects.all():
            assert backup.original_item != backup.normalized_item
            # 현재 expense.item == normalized
            exp = Expense.objects.get(id=backup.expense_id)
            assert exp.item == backup.normalized_item

    def test_forwards_does_not_touch_non_candidates(self, historical_model):
        Expense = historical_model("Expense")
        ids = _seed_expenses(historical_model)

        _migrate_to(AFTER)

        # PLAIN/OLD/잔액/'(주)이마트' 는 그대로
        unchanged = {s[0] for s in SEED if s[0] == s[1]}
        items = set(Expense.objects.filter(id__in=ids).values_list("item", flat=True))
        assert unchanged.issubset(items)

    # ── idempotency ────────────────────────────────────────
    def test_forwards_idempotent(self, historical_model):
        """0005 forwards 를 직접 한 번 더 호출해도 무변화 + 백업 중복 없음."""
        import importlib

        from django.apps import apps as global_apps

        Expense = historical_model("Expense")
        Backup = historical_model("ExpenseItemBackup")
        ids = _seed_expenses(historical_model)

        _migrate_to(AFTER)
        first_items = dict(
            Expense.objects.filter(id__in=ids).values_list("id", "item")
        )
        first_backup_count = Backup.objects.count()

        # 마이그레이션 모듈의 forwards 를 그대로 재호출 (RunPython 2회 적용 모사).
        mig = importlib.import_module(
            "expenses.migrations.0005_normalize_sms_items"
        )
        mig.forwards(global_apps, None)

        second_items = dict(
            Expense.objects.filter(id__in=ids).values_list("id", "item")
        )
        assert first_items == second_items
        # 이미 백업된 expense 는 건너뛰므로 백업 건수도 동일 (중복 백업 없음)
        assert Backup.objects.count() == first_backup_count

    # ── backwards ──────────────────────────────────────────
    def test_backwards_restores_originals(self, historical_model):
        Expense = historical_model("Expense")
        Backup = historical_model("ExpenseItemBackup")
        ids = _seed_expenses(historical_model)

        _migrate_to(AFTER)
        assert Backup.objects.count() == 3

        # 되돌리기
        _migrate_to(BEFORE)

        for idx, (original, _expected) in enumerate(SEED):
            obj = Expense.objects.get(id=ids[idx])
            assert obj.item == original, (
                f"restore failed: got {obj.item!r}, expected {original!r}"
            )
        # 백업은 정리됨
        assert Backup.objects.count() == 0
