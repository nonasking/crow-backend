from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from receivers.constants import ParseSMSErrorMessages
from receivers.externals.notion.api_client import NotionClient
from receivers.services.parse_sms_service import ParseSMSService


class SMSReceiverPostSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)

    def validate_message(self, value):
        """
        메시지 파싱이 가능한지 검증합니다.
        """
        try:
            service = ParseSMSService(value)
            # 파싱 결과를 인스턴스 변수에 임시 저장하여 나중에 활용
            self.parsed_result = service.parse()
        except ValueError as e:
            raise ValidationError(f"{ParseSMSErrorMessages.PARSE_FAILED}{str(e)}")

        return value

    def save_to_notion(self):
        """
        검증된 데이터를 Notion에 업로드합니다.
        """
        client = NotionClient()
        try:
            client.create_card_record(self.parsed_result)
        except RuntimeError:
            raise ValidationError(ParseSMSErrorMessages.NOTION_FAILED)

        return self.parsed_result
