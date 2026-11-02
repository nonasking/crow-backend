from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response


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
    except IntegrityError:
        return Response(
            {"detail": "이미 있는 레코드와 겹칩니다. skip_duplicates=true로 다시 실행하세요."},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(result)
