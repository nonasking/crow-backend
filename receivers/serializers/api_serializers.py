from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError

from receivers.constants import ParseSMSErrorMessages
from receivers.services.card_payment_service import record_card_payment
from receivers.services.parse_sms_service import ParseSMSService


class NotionUnavailable(APIException):
    """Notion 기록 실패. 포워더가 재시도할 수 있도록 5xx로 응답한다."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = ParseSMSErrorMessages.NOTION_FAILED
    default_code = "notion_unavailable"


class SMSReceiverPostSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_result: dict | None = None
        self.ignored_reason: str | None = None

    def validate_message(self, value):
        """
        메시지 파싱이 가능한지 검증합니다.
        승인취소 문자는 오류가 아니라 기록하지 않을 대상으로 표시합니다.
        """
        service = ParseSMSService(value)
        if service.is_cancellation():
            self.ignored_reason = ParseSMSErrorMessages.CANCELLATION_IGNORED
            return value

        try:
            # 파싱 결과를 인스턴스 변수에 임시 저장하여 나중에 활용
            self.parsed_result = service.parse(enum_representation="value")
        except ValueError as e:
            raise ValidationError(f"{ParseSMSErrorMessages.PARSE_FAILED}{e}")

        return value

    def save_payment(self):
        """
        검증된 결제 정보를 Expense와 Notion에 기록합니다.
        """
        try:
            return record_card_payment(self.parsed_result)
        except RuntimeError:
            raise NotionUnavailable()
