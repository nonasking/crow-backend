"""
카드 결제 SMS 파싱 결과를 Notion과 Expense에 기록하는 서비스.
"""

from datetime import date

from django.utils import timezone

from expenses.constants import (
    LOCAL_TIMEZONE,
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)
from expenses.models import Expense
from receivers.externals.notion.api_client import NotionClient


def resolve_spent_at(spent_at: str, today: date | None = None) -> date:
    """SMS의 'MM/DD'를 실제 결제일로 변환합니다.

    SMS에는 연도가 없으므로 올해로 붙이되, 미래 날짜가 되면 작년 결제로 봅니다.
    날짜를 추출하지 못한 경우(빈 문자열 등)에는 오늘 날짜를 반환합니다.
    '오늘'은 SMS와 같은 한국 시간 기준입니다. 서버 시간(UTC)으로 판단하면
    KST 00:00~08:59 결제가 미래 날짜로 보여 작년으로 기록됩니다.

    Examples:
        >>> resolve_spent_at("02/23", today=date(2026, 3, 1))
        datetime.date(2026, 2, 23)
        >>> resolve_spent_at("12/31", today=date(2027, 1, 2))
        datetime.date(2026, 12, 31)
    """
    today = today or timezone.localdate(timezone=LOCAL_TIMEZONE)
    try:
        month, day = (int(part) for part in spent_at.split("/"))
    except ValueError:
        return today

    for year in (today.year, today.year - 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            # 2/29처럼 해당 연도에 없는 날짜
            continue
        if candidate <= today:
            return candidate
    return today


def record_card_payment(parsed: dict) -> Expense:
    """파싱된 결제 정보를 Notion에 기록하고 UNSETTLED Expense로 저장합니다.

    Args:
        parsed: ParseSMSService(...).parse(enum_representation="value") 결과

    Raises:
        RuntimeError: Notion API 요청 실패 시 (이 경우 Expense는 저장하지 않음)
    """
    record = {**parsed, "spent_at": resolve_spent_at(parsed["spent_at"])}
    payment_method = ExpensePaymentMethodEnum(record["payment_method"])

    NotionClient().create_card_record(
        {**record, "payment_method": payment_method.label}
    )

    # TODO 테스트용 로직: 별도 api로 분리 예정
    return Expense.objects.create(
        **record,
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseSubCategoryEnum.UNSETTLED,
    )
