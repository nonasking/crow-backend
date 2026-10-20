from django.db import IntegrityError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from expenses.filters import BudgetFilter
from expenses.models import Budget
from expenses.pagination import DefaultPagination
from expenses.serializers.api_serializers import NotionBudgetMigrateSerializer
from expenses.serializers.model_serializers import BudgetSerializer
from expenses.views.notion_migration import run_notion_migration


@extend_schema_view(
    create=extend_schema(summary="Budget 생성"),
    list=extend_schema(summary="Budget 목록 조회"),
    retrieve=extend_schema(summary="Budget 단건 조회"),
    update=extend_schema(summary="Budget 수정"),
    partial_update=extend_schema(summary="Budget 단건 수정"),
    destroy=extend_schema(summary="Budget 삭제"),
)
class BudgetViewSet(ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

    pagination_class = DefaultPagination

    filterset_class = BudgetFilter
    ordering_fields = ["year", "month", "category", "amount", "created_at"]
    ordering = ["-year", "-month", "category"]

    def perform_create(self, serializer):
        self._save_or_raise_duplicate(serializer)

    def perform_update(self, serializer):
        self._save_or_raise_duplicate(serializer)

    @staticmethod
    def _save_or_raise_duplicate(serializer):
        # validate 단계의 중복 검사와 save 사이 경쟁 상태로 UniqueConstraint에 걸리는 경우
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                "해당 연도/월/카테고리/소분류 조합의 예산이 이미 존재합니다."
            )

    @extend_schema(
        summary="Notion data > Budget 모델로 마이그레이션",
        request=NotionBudgetMigrateSerializer,
    )
    @action(detail=False, methods=["post"], url_path="migrate-budget-from-notion")
    def migrate_budget_from_notion(self, request, *args, **kwargs):
        return run_notion_migration(NotionBudgetMigrateSerializer, request.data)
