from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response


BUDGET_UNIQUE_CONSTRAINT = "unique_budget_per_month"


def _constraint_name(error: IntegrityError) -> str:
    """psycopg가 알려 주는 제약 이름. 없으면 메시지 전체로 대신한다."""
    diag = getattr(error.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) or str(error)


def run_notion_migration(serializer_class, data) -> Response:
    """Notion → DB 마이그레이션 시리얼라이저를 실행하고, Notion 오류는 502로 응답한다."""
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    try:
        # 일부만 들어간 채로 끝나지 않도록 한 번에 커밋하거나 전부 되돌린다.
        with transaction.atomic():
            result = serializer.save()
    except RuntimeError as e:
        return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
    except IntegrityError as e:
        # 예산의 (연, 월, 대분류, 소분류) unique 제약 위반만 사용자가 고칠 수 있는 충돌이다.
        # 그 밖의 제약 위반은 안내 문구가 맞지 않으므로 그대로 올린다(500 + 로그).
        if BUDGET_UNIQUE_CONSTRAINT not in _constraint_name(e):
            raise
        return Response(
            {"detail": "이미 있는 예산과 겹칩니다. skip_duplicates=true로 다시 실행하세요."},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(result)
