from rest_framework import serializers

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
