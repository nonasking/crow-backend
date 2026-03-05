from datetime import date, datetime

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from expenses.constants import ExpenseCategoryEnum, ExpenseSubCategoryEnum
from expenses.models import Expense
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
            self.parsed_result_for_db = service.parse(enum_representation="value")
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

        # TODO 테스트용 로직: 별도 api로 분리 예정
        parsed_result = self.parsed_result
        spent_at_str = parsed_result["spent_at"]
        parsed_result["spent_at"] = self._convert_spent_at(spent_at_str)
        Expense.objects.create(
            **parsed_result,
            category=ExpenseCategoryEnum.UNSETTLED,
            sub_category=ExpenseSubCategoryEnum.UNSETTLED,
        )

        return self.parsed_result

    def _convert_spent_at(self, spent_at_str: str) -> str:
        """
        '02/23' -> '2026-02-23' 형태로 변환
        미래 날짜면 작년으로 보정
        """
        today = date.today()
        year = today.year

        parsed = datetime.strptime(f"{year}/{spent_at_str}", "%Y/%m/%d").date()

        # 미래 날짜면 작년 사용으로 판단
        if parsed > today:
            parsed = parsed.replace(year=year - 1)

        return parsed.strftime("%Y-%m-%d")
