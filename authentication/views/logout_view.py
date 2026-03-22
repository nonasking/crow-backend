from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # refresh token을 블랙리스트에 추가하려면 simplejwt blacklist 앱 필요
        # 현재는 클라이언트에서 토큰 삭제로 처리 (단순 구조)
        return Response({"detail": "로그아웃 되었습니다."})
