from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from receivers.serializers.sms_receiver_post_serializer import SMSReceiverPostSerializer


class SMSReceiverView(APIView):
    @extend_schema(
        summary="카드 결제 SMS 수신",
        request=SMSReceiverPostSerializer,
        description="카드사로부터 받은 SMS 전문을 전달받아 파싱 후 Notion에 기록합니다.",
        responses={status.HTTP_200_OK: "성공 응답"},
    )
    def post(self, request: Request) -> Response:
        serializer = SMSReceiverPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save_to_notion()
        return Response({"status": "success"}, status=status.HTTP_200_OK)
