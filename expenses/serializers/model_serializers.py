from rest_framework import serializers

from expenses.constants import CATEGORY_SUBCATEGORY_MAP
from expenses.models import Budget
from expenses.models.expense import Expense


class ExpenseSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        # PATCH 시 부분 업데이트 고려 — 기존 값 fallback
        instance = self.instance
        category = attrs.get("category", instance.category if instance else None)
        sub_category = attrs.get(
            "sub_category", instance.sub_category if instance else None
        )

        if category and sub_category:
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

        return attrs

class BudgetSerializer(serializers.ModelSerializer):
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
        # PATCH 시 부분 업데이트 고려 — 기존 값 fallback
        instance = self.instance
        category = attrs.get("category", instance.category if instance else None)
        sub_category = attrs.get(
            "sub_category", instance.sub_category if instance else None
        )

        if category and sub_category:
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

        return attrs
