from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from receivers.permissions import WEBHOOK_TOKEN_HEADER, HasWebhookToken
from receivers.serializers.api_serializers import SMSReceiverPostSerializer


class SMSReceiverView(APIView):
    # 포워더 앱은 JWT를 보내지 않으므로 인증 클래스 없이 공유 토큰으로 검증한다.
    authentication_classes = []
    permission_classes = [HasWebhookToken]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "sms_webhook"

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
        responses={status.HTTP_200_OK: "성공 응답"},
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
