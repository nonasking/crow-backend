from rest_framework import serializers

from expenses.models import Budget


class BudgetService:
    """Budget 도메인 비즈니스 로직을 담당하는 서비스 클래스."""

    @staticmethod
    def check_duplicate_budget(
        year: int,
        month: int,
        category: str,
        sub_category: str,
        exclude_id: int | None = None,
    ) -> None:
        """
        중복 예산 사전 검증 (UniqueConstraint 도달 전에 사용자 친화적 오류 반환).
        - DB 쿼리로 동일 year+month+category+sub_category 조합 존재 여부 확인
        - exclude_id: 수정(PUT/PATCH) 시 자기 자신 제외
        - 위반 시: ValidationError (non_field_errors)
        """
        qs = Budget.objects.filter(
            year=year,
            month=month,
            category=category,
            sub_category=sub_category,
        )
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)

        if qs.exists():
            raise serializers.ValidationError(
                f"{year}년 {month}월 {category} / {sub_category} 예산이 이미 존재합니다."
            )
