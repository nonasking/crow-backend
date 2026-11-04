from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutView(APIView):
    """로그아웃: 받은 refresh 토큰을 blacklist에 넣어 더는 access를 발급받지 못하게 한다.

    refresh 토큰(7일)이 /auth/refresh/로 access를 다시 받을 수 있는 자격 증명이 되었으므로,
    클라이언트가 쿠키를 지우는 것만으로는 새어 나간 토큰을 막을 수 없다.
    access가 이미 만료된 뒤에도 로그아웃할 수 있도록 인증은 요구하지 않는다
    (refresh 토큰을 가진 쪽만 그 토큰을 무효화할 수 있다).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="로그아웃 (refresh 토큰 무효화)",
        auth=[],
        request={
            "application/json": {
                "type": "object",
                "properties": {"refresh": {"type": "string"}},
            }
        },
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                # 이미 만료됐거나 잘못된 토큰이면 무효화할 것도 없다.
                pass
        return Response({"detail": "로그아웃 되었습니다."})
