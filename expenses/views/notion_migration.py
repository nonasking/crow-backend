from rest_framework import status
from rest_framework.response import Response


def run_notion_migration(serializer_class, data) -> Response:
    """Notion → DB 마이그레이션 시리얼라이저를 실행하고, Notion 오류는 502로 응답한다."""
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    try:
        result = serializer.save()
    except RuntimeError as e:
        return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(result)
