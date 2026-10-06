from rest_framework import serializers

from expenses.constants import CATEGORY_SUBCATEGORY_MAP
from expenses.models import Budget
from expenses.models.expense import Expense
from expenses.services.budget_service import BudgetService


class CategoryValidationMixin:
    def _resolve(self, attrs, field):
        # PATCH 시 부분 업데이트 고려 — 기존 값 fallback
        return attrs.get(field, getattr(self.instance, field, None))

    @staticmethod
    def _check_category_subcategory(category, sub_category):
        if not (category and sub_category):
            return

        allowed_subs = CATEGORY_SUBCATEGORY_MAP.get(category, [])
        if sub_category not in allowed_subs:
            raise serializers.ValidationError(
                {
                    "sub_category": (
                        f"'{sub_category}'은(는) '{category}' 카테고리의 "
                        f"올바른 소분류가 아닙니다. "
                        f"허용된 소분류: {allowed_subs}"
                    )
                }
            )


class ExpenseSerializer(CategoryValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            "id",
            "spent_at",
            "category",
            "sub_category",
            "item",
            "payment_method",
            "amount",
            "memo",
            "auto_classified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["auto_classified"]

    def validate(self, attrs):
        self._check_category_subcategory(
            self._resolve(attrs, "category"), self._resolve(attrs, "sub_category")
        )
        return attrs


class BudgetSerializer(CategoryValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = [
            "id",
            "year",
            "month",
            "category",
            "sub_category",
            "amount",
            "memo",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        category = self._resolve(attrs, "category")
        sub_category = self._resolve(attrs, "sub_category")
        year = self._resolve(attrs, "year")
        month = self._resolve(attrs, "month")
        amount = self._resolve(attrs, "amount")

        # 연도 범위 검증 (BR-02)
        if year is not None:
            BudgetService.validate_year_range(year)

        # 금액 양수 검증 (BR-04)
        if amount is not None:
            BudgetService.validate_amount_positive(amount)

        # 카테고리-소분류 매핑 검증 (BR-01)
        self._check_category_subcategory(category, sub_category)

        # 중복 예산 사전 검증 (BR-05)
        if year is not None and month is not None and category and sub_category:
            BudgetService.check_duplicate_budget(
                year=year,
                month=month,
                category=category,
                sub_category=sub_category,
                exclude_id=getattr(self.instance, "id", None),
            )

        return attrs
