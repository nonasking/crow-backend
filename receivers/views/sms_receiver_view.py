from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from receivers.permissions import WEBHOOK_TOKEN_HEADER, HasWebhookToken
from receivers.serializers.api_serializers import SMSReceiverPostSerializer
from receivers.throttling import SMSWebhookThrottle


class SMSReceiverView(APIView):
    # 포워더 앱은 JWT를 보내지 않으므로 인증 클래스 없이 공유 토큰으로 검증한다.
    authentication_classes = []
    permission_classes = [HasWebhookToken]
    throttle_classes = [SMSWebhookThrottle]

    def check_permissions(self, request):
        # DRF는 권한 검사 뒤에 throttle을 검사한다. 그러면 틀린 토큰으로 보내는
        # 요청은 403만 받고 rate limit에 걸리지 않으므로, 순서를 바꿔 토큰 추측도
        # 한도 안에서만 가능하게 한다.
        super().check_throttles(request)
        super().check_permissions(request)

    def check_throttles(self, request):
        # check_permissions에서 이미 검사했다. 두 번 세지 않도록 비워 둔다.
        pass

    @extend_schema(
        summary="카드 결제 SMS 수신",
        request=SMSReceiverPostSerializer,
        parameters=[
            OpenApiParameter(
                name=WEBHOOK_TOKEN_HEADER,
                location=OpenApiParameter.HEADER,
                required=False,
                description="SMS_WEBHOOK_TOKEN과 같은 공유 토큰. 헤더를 못 쓰면 ?token= 으로 보낸다.",
            ),
        ],
        description=(
            "카드사로부터 받은 SMS 전문을 전달받아 파싱 후 Expense와 Notion에 기록합니다. "
            "승인취소 문자는 기록하지 않고 status=ignored로 응답합니다."
        ),
        responses={
            status.HTTP_200_OK: "기록 성공(status=success) 또는 승인취소 무시(status=ignored)",
            status.HTTP_400_BAD_REQUEST: "메시지 파싱 실패",
            status.HTTP_403_FORBIDDEN: "웹훅 토큰 없음 또는 불일치",
            status.HTTP_429_TOO_MANY_REQUESTS: "rate limit 초과",
            status.HTTP_503_SERVICE_UNAVAILABLE: "Notion 기록 실패(재시도 가능)",
        },
    )
    def post(self, request: Request) -> Response:
        serializer = SMSReceiverPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.ignored_reason:
            return Response(
                {"status": "ignored", "reason": serializer.ignored_reason},
                status=status.HTTP_200_OK,
            )

        serializer.save_payment()
        return Response({"status": "success"}, status=status.HTTP_200_OK)
