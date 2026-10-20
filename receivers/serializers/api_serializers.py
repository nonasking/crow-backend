from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from receivers.constants import ParseSMSErrorMessages
from receivers.services.card_payment_service import record_card_payment
from receivers.services.parse_sms_service import ParseSMSService


class SMSReceiverPostSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)

    def validate_message(self, value):
        """
        메시지 파싱이 가능한지 검증합니다.
        """
        try:
            # 파싱 결과를 인스턴스 변수에 임시 저장하여 나중에 활용
            self.parsed_result = ParseSMSService(value).parse(
                enum_representation="value"
            )
        except ValueError as e:
            raise ValidationError(f"{ParseSMSErrorMessages.PARSE_FAILED}{e}")

        return value

    def save_payment(self):
        """
        검증된 결제 정보를 Notion과 Expense에 기록합니다.
        """
        try:
            return record_card_payment(self.parsed_result)
        except RuntimeError:
            raise ValidationError(ParseSMSErrorMessages.NOTION_FAILED)
