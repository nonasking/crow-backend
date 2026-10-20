from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from expenses.constants import (
    CATEGORY_SUBCATEGORY_MAP,
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)
from expenses.filters import ExpenseFilter
from expenses.models.expense import Expense
from expenses.pagination import DefaultPagination
from expenses.serializers.api_serializers import (
    ExpenseSummarySerializer,
    NotionExpenseMigrateSerializer,
)
from expenses.serializers.model_serializers import ExpenseSerializer
from expenses.views.notion_migration import run_notion_migration


@extend_schema_view(
    create=extend_schema(summary="Expense 생성"),
    list=extend_schema(summary="Expense 목록 조회"),
    retrieve=extend_schema(summary="Expense 단건 조회"),
    update=extend_schema(summary="Expense 수정"),
    partial_update=extend_schema(summary="Expense 단건 수정"),
    destroy=extend_schema(summary="Expense 삭제"),
)
class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    pagination_class = DefaultPagination

    filterset_class = ExpenseFilter

    ordering_fields = [
        "spent_at",
        "amount",
        "category",
        "sub_category",
        "payment_method",
    ]
    ordering = ["-spent_at"]

    @extend_schema(
        summary="Notion data > Expense 모델로 마이그레이션",
        request=NotionExpenseMigrateSerializer,
    )
    @action(detail=False, methods=["post"], url_path="migrate-expenses-from-notion")
    def migrate_expenses_from_notion(self, request, *args, **kwargs):
        return run_notion_migration(NotionExpenseMigrateSerializer, request.data)

    @extend_schema(
        summary="카테고리 / 서브카테고리 / 결제수단 값 조회",
    )
    @action(detail=False, methods=["get"])
    def options(self, request):
        def to_options(enum):
            return [{"value": value, "label": label} for value, label in enum.choices]

        return Response(
            {
                "categories": to_options(ExpenseCategoryEnum),
                "sub_categories": to_options(ExpenseSubCategoryEnum),
                "payment_methods": to_options(ExpensePaymentMethodEnum),
                "category_subcategory_map": {
                    category: list(sub_categories)
                    for category, sub_categories in CATEGORY_SUBCATEGORY_MAP.items()
                },
            }
        )

    @extend_schema(summary="지출 요약 조회")
    @action(detail=False, methods=["get"], serializer_class=ExpenseSummarySerializer)
    def summary(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.summary())
