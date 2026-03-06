from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from expenses.filters import BudgetFilter
from expenses.models import Budget
from expenses.pagination import BudgetPagination
from expenses.serializers.api_serializers import NotionBudgetMigrateSerializer
from expenses.serializers.model_serializers import BudgetSerializer


class BudgetViewSet(ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

    pagination_class = BudgetPagination

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = BudgetFilter

    ordering_fields = [
        "spent_at",
        "amount",
        "category",
        "sub_category",
        "payment_method",
    ]
    ordering = ["-spent_at"]

    @extend_schema(summary="Budget 생성")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Budget 목록 조회")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Budget 단건 조회")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Budget 수정")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Budget 단건 수정")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Budget 삭제")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Notion data > Budget 모델로 마이그레이션",
        request=NotionBudgetMigrateSerializer,
    )
    @action(detail=False, methods=["post"], url_path="migrate-budget-from-notion")
    def migrate_budget_from_notion(self, request, *args, **kwargs):
        serializer = NotionBudgetMigrateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = serializer.save()
        except RuntimeError as e:
            return Response({"detail": str(e)}, status=502)
        return Response(result)
