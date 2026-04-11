import pytest
from rest_framework import status
from rest_framework.test import APIClient

from expenses.constants import ExpenseCategoryEnum, ExpenseSubCategoryEnum
from expenses.models import Budget


# ---------------------------------------------------------------------------
# Helper: 유효한 Budget 생성 페이로드
# ---------------------------------------------------------------------------
def _valid_budget_payload(**overrides):
    """기본 유효 데이터를 반환하며, overrides 로 원하는 필드만 덮어쓸 수 있다."""
    base = {
        "year": 2026,
        "month": 4,
        "category": ExpenseCategoryEnum.FOOD,
        "sub_category": ExpenseSubCategoryEnum.DINING_OUT,
        "amount": 500000,
        "memo": "테스트 예산",
    }
    base.update(overrides)
    return base


URL = "/expenses/budget/"


def _detail_url(pk):
    return f"{URL}{pk}/"


# ===========================================================================
# 기존 테스트 (유지)
# ===========================================================================
@pytest.mark.django_db
def test_list_budget(auth_client):
    Budget.objects.create(
        amount=1,
        year=2024,
        month=1,
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )
    Budget.objects.create(
        amount=1,
        year=2024,
        month=2,
        category=ExpenseCategoryEnum.ALLOWANCE,
        sub_category=ExpenseSubCategoryEnum.ALLOWANCE_MS,
    )
    Budget.objects.create(
        amount=1,
        year=2024,
        month=3,
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )

    response = auth_client.get(f"{URL}?category=UNSETTLED&sub_category=UNSETTLED")
    assert response.status_code == status.HTTP_200_OK
    assert response.data.get("count") == 2


# ===========================================================================
# CRUD 테스트
# ===========================================================================
@pytest.mark.django_db
class TestBudgetCRUD:
    """Budget 리소스 기본 CRUD 동작 검증."""

    # ── List ───────────────────────────────────────────
    def test_list_returns_200(self, auth_client):
        response = auth_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_list_unauthenticated_returns_401(self):
        client = APIClient()  # 인증 없는 클라이언트
        response = client.get(URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── Create ─────────────────────────────────────────
    def test_create_valid_returns_201(self, auth_client):
        payload = _valid_budget_payload()
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["year"] == 2026
        assert response.data["month"] == 4
        assert response.data["category"] == ExpenseCategoryEnum.FOOD
        assert response.data["sub_category"] == ExpenseSubCategoryEnum.DINING_OUT
        assert response.data["amount"] == 500000
        assert Budget.objects.filter(id=response.data["id"]).exists()

    def test_create_duplicate_returns_400(self, auth_client):
        """동일 year+month+category+sub_category 조합으로 두 번 생성 시 400."""
        payload = _valid_budget_payload()
        resp1 = auth_client.post(URL, payload, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED

        resp2 = auth_client.post(URL, payload, format="json")
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in resp2.data

    # ── Retrieve ───────────────────────────────────────
    def test_retrieve_returns_200(self, auth_client):
        budget = Budget.objects.create(**_valid_budget_payload())
        response = auth_client.get(_detail_url(budget.pk))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == budget.pk

    # ── Partial Update ─────────────────────────────────
    def test_partial_update_amount_returns_200(self, auth_client):
        budget = Budget.objects.create(**_valid_budget_payload())
        response = auth_client.patch(
            _detail_url(budget.pk), {"amount": 600000}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        budget.refresh_from_db()
        assert budget.amount == 600000

    def test_partial_update_keeps_other_fields(self, auth_client):
        """PATCH amount 만 변경하면 나머지 필드는 기존 값을 유지해야 한다."""
        budget = Budget.objects.create(**_valid_budget_payload())
        original_year = budget.year
        original_month = budget.month
        original_category = budget.category
        original_sub_category = budget.sub_category

        auth_client.patch(
            _detail_url(budget.pk), {"amount": 700000}, format="json"
        )
        budget.refresh_from_db()
        assert budget.year == original_year
        assert budget.month == original_month
        assert budget.category == original_category
        assert budget.sub_category == original_sub_category

    # ── Full Update ────────────────────────────────────
    def test_update_put_returns_200(self, auth_client):
        budget = Budget.objects.create(**_valid_budget_payload())
        payload = _valid_budget_payload(amount=800000, memo="PUT 수정")
        response = auth_client.put(_detail_url(budget.pk), payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        budget.refresh_from_db()
        assert budget.amount == 800000
        assert budget.memo == "PUT 수정"

    def test_update_put_missing_field_returns_400(self, auth_client):
        """PUT 요청 시 필수 필드(amount) 누락 → 400."""
        budget = Budget.objects.create(**_valid_budget_payload())
        payload = _valid_budget_payload()
        del payload["amount"]
        response = auth_client.put(_detail_url(budget.pk), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount" in response.data

    # ── Destroy ────────────────────────────────────────
    def test_destroy_returns_204(self, auth_client):
        budget = Budget.objects.create(**_valid_budget_payload())
        response = auth_client.delete(_detail_url(budget.pk))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Budget.objects.filter(id=budget.pk).exists()


# ===========================================================================
# 유효성 검사 테스트
# ===========================================================================
@pytest.mark.django_db
class TestBudgetValidation:
    """BudgetSerializer + BudgetService 유효성 검사 규칙 검증."""

    # ── 연도 범위 (BR-02) ──────────────────────────────
    def test_create_invalid_year_below_2000_returns_400(self, auth_client):
        payload = _valid_budget_payload(year=1999)
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "year" in response.data

    def test_create_invalid_year_above_2100_returns_400(self, auth_client):
        payload = _valid_budget_payload(year=2101)
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "year" in response.data

    # ── 금액 양수 (BR-04) ─────────────────────────────
    def test_create_zero_amount_returns_400(self, auth_client):
        payload = _valid_budget_payload(amount=0)
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount" in response.data

    def test_create_negative_amount_returns_400(self, auth_client):
        payload = _valid_budget_payload(amount=-1000)
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount" in response.data

    # ── 카테고리-소분류 매핑 (BR-01) ───────────────────
    def test_create_invalid_subcategory_returns_400(self, auth_client):
        """FOOD 카테고리에 TRANSPORT 소분류 → 400."""
        payload = _valid_budget_payload(
            category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.TRANSPORT,
        )
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "sub_category" in response.data

    # ── 중복 검증 - PATCH (BR-05) ─────────────────────
    def test_partial_update_duplicate_returns_400(self, auth_client):
        """기존 Budget A 가 있을 때, Budget B 를 PATCH 해서 A 와 같은 조합으로 만들면 400."""
        Budget.objects.create(
            year=2026,
            month=4,
            category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.DINING_OUT,
            amount=100000,
        )
        budget_b = Budget.objects.create(
            year=2026,
            month=4,
            category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.COOKING,
            amount=200000,
        )
        # B 의 sub_category 를 A 와 동일하게 변경 시도
        response = auth_client.patch(
            _detail_url(budget_b.pk),
            {"sub_category": ExpenseSubCategoryEnum.DINING_OUT},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

    def test_update_same_record_does_not_raise_duplicate(self, auth_client):
        """자기 자신의 amount 만 수정할 때 중복 오류가 발생하면 안 된다."""
        budget = Budget.objects.create(**_valid_budget_payload())
        response = auth_client.patch(
            _detail_url(budget.pk), {"amount": 999999}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        budget.refresh_from_db()
        assert budget.amount == 999999


# ===========================================================================
# 필터 테스트
# ===========================================================================
@pytest.mark.django_db
class TestBudgetFilter:
    """BudgetFilter 의 필터링 동작 검증."""

    def test_filter_by_year_and_month(self, auth_client):
        Budget.objects.create(
            year=2025, month=1, category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.DINING_OUT, amount=100000,
        )
        Budget.objects.create(
            year=2026, month=4, category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.COOKING, amount=200000,
        )
        Budget.objects.create(
            year=2026, month=5, category=ExpenseCategoryEnum.TRANSPORT,
            sub_category=ExpenseSubCategoryEnum.TRANSPORT, amount=50000,
        )

        response = auth_client.get(URL, {"year": 2026, "month": 4})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["year"] == 2026
        assert response.data["results"][0]["month"] == 4

    def test_filter_by_category(self, auth_client):
        Budget.objects.create(
            year=2026, month=4, category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.DINING_OUT, amount=100000,
        )
        Budget.objects.create(
            year=2026, month=4, category=ExpenseCategoryEnum.TRANSPORT,
            sub_category=ExpenseSubCategoryEnum.TRANSPORT, amount=50000,
        )
        Budget.objects.create(
            year=2026, month=4, category=ExpenseCategoryEnum.FOOD,
            sub_category=ExpenseSubCategoryEnum.COOKING, amount=200000,
        )

        response = auth_client.get(URL, {"category": "FOOD"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        for item in response.data["results"]:
            assert item["category"] == "FOOD"
