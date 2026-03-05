from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from expenses.constants import (
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum, CATEGORY_SUBCATEGORY_MAP,
)
from expenses.filters import ExpenseFilter
from expenses.models.expense import Expense
from expenses.pagination import ExpensePagination
from expenses.serializers.api_serializers import NotionMigrateSerializer
from expenses.serializers.model_serializers import ExpenseSerializer


class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    pagination_class = ExpensePagination

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ExpenseFilter

    ordering_fields = [
        "spent_at",
        "amount",
        "category",
        "sub_category",
        "payment_method",
    ]
    ordering = ["-spent_at"]

    @extend_schema(summary="Expense 생성")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Expense 목록 조회")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Expense 단건 조회")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Expense 수정")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Expense 단건 수정")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Expense 삭제")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Notion data > Expense 모델로 마이그레이션",
        request=NotionMigrateSerializer,
    )
    @action(detail=False, methods=["post"], url_path="migrate-from-notion")
    def migrate_from_notion(self, request, *args, **kwargs):
        serializer = NotionMigrateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = serializer.save()
        except RuntimeError as e:
            return Response({"detail": str(e)}, status=502)
        return Response(result)

    @extend_schema(
        summary="카테고리 / 서브카테고리 / 결제수단 값 조회",
    )
    @action(detail=False, methods=["get"])
    def options(self, request):
        return Response(
            {
                "categories": [
                    {"value": value, "label": label}
                    for value, label in ExpenseCategoryEnum.choices
                ],
                "sub_categories": [
                    {"value": value, "label": label}
                    for value, label in ExpenseSubCategoryEnum.choices
                ],
                "payment_methods": [
                    {"value": value, "label": label}
                    for value, label in ExpensePaymentMethodEnum.choices
                ],
                "category_subcategory_map": {
                    category: list(sub_categories)
                    for category, sub_categories in CATEGORY_SUBCATEGORY_MAP.items()
                },
            }
        )
