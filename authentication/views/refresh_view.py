from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenRefreshView


@extend_schema(summary="access 토큰 갱신", auth=[])
class RefreshView(TokenRefreshView):
    """refresh 토큰으로 새 access 토큰을 발급한다.

    로그인 때 받은 refresh 토큰(7일)이 유효한 동안은 access(24시간)가 만료돼도
    다시 로그인하지 않아도 된다. 인증 헤더는 보지 않는다(TokenViewBase 기본값).
    ROTATE_REFRESH_TOKENS=False라 응답에는 access만 들어 있다.
    """
