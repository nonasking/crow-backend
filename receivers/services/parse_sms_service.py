"""
receivers/services.py

카드사 결제 문자를 파싱하는 서비스 클래스.
"""

import re
from decimal import Decimal
from typing import Literal

from expenses.constants import ExpensePaymentMethodEnum
from receivers.constants import ParseSMSErrorMessages

# SMS 가맹점명 정규화용 정규식
# 예) "(일시불)06/20 카페63도" / "(할부3개월)06/03 20:52 (주)이마트"
#  - 그룹1: 마커 + 날짜(+선택적 시간)를 걷어낸 나머지(가맹점명)
_SMS_MERCHANT_PATTERN = re.compile(
    r"^\((?:일시불|할부[^)]*)\)\s*\d{1,2}/\d{1,2}\s*(?:\d{1,2}:\d{2}\s*)?(.*)$"
)

# 법인격 표기 제거용 정규식: "(주)", "주식회사", "㈜"
_CORPORATE_FORM_PATTERN = re.compile(r"\(주\)|주식회사|㈜")

_WHITESPACE_PATTERN = re.compile(r"\s+")

# 신한 패턴2 가맹점: 'HH:MM' 뒤부터 '잔액' 앞(또는 줄 끝)까지.
# 문자 클래스 [^잔액]으로 쓰면 '잔'·'액' 글자 하나하나를 제외하므로
# "잔치국수"가 빈 문자열, "카페액자"가 "카페"로 잘린다.
_SHINHAN_PAREN_LOCATION_PATTERN = re.compile(r"\d{2}:\d{2}\s+(?!잔액)(.+?)(?=\s*잔액|\s*$)")

# 신한 해외승인: "신한(4557)해외승인 강*성 KRW 37,730 (US)11/11 13:56 ELEVENLABS 누적1,682,643원"
#       "신한(4557)해외승인 강*성 220.00 달러 (US)11/11 22:34 ANTHROPIC* 누적2,027,221원"
#  - 금액은 "KRW 37,730"(원화) 또는 "220.00 달러"(외화) 형식이다.
#    외화 금액은 파서에서 환산하지 않고 foreign_amount/currency로 넘긴다.
#  - 가맹점은 'MM/DD HH:MM' 뒤부터 '누적' 앞(또는 줄 끝)까지.
_SHINHAN_OVERSEAS_PATTERN = re.compile(r"신한\(\d+\)해외승인")
_SHINHAN_OVERSEAS_AMOUNT_PATTERN = re.compile(r"\bKRW\s*(\d[\d,]*)")
_SHINHAN_OVERSEAS_FOREIGN_AMOUNT_PATTERN = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(달러)(?=\s|\(|$)"
)
# 문자에 찍히는 통화 단위 → ISO 4217 코드
_FOREIGN_CURRENCY_CODES = {"달러": "USD"}
_SHINHAN_OVERSEAS_LOCATION_PATTERN = re.compile(
    r"\d{2}/\d{2}\s+\d{2}:\d{2}\s+(?!누적)(.+?)(?=\s*누적|\s*$)", re.MULTILINE
)

# 승인취소 문자 판별: "승인취소" 또는 카드번호 괄호 바로 뒤의 "취소".
# 문자 전체에서 "취소"를 찾으면 가맹점명("취소불가상점")이나 적요("예약취소수수료")에
# 걸려 정상 지출이 기록되지 않는다.
_CANCELLATION_PATTERN = re.compile(r"승인\s*취소|\(\d+\)\s*취소")

# Expense.item(max_length=100)에 맞춘 길이 상한
ITEM_MAX_LENGTH = 100


def normalize_merchant(item: str) -> str:
    """SMS 포맷의 가맹점 항목 문자열을 깨끗한 가맹점명으로 정규화합니다.

    `(일시불)`/`(할부 N개월)` 마커와 앞쪽 날짜(`MM/DD`), 선택적 시간(`HH:MM`)을
    제거하고 법인격 표기(`(주)`, `주식회사`, `㈜`)를 제거한 뒤 공백을 정리합니다.

    SMS 포맷에 매칭되지 않는 입력(PLAIN/OLD/잔액 행 등)은 **원본 그대로** 반환합니다.

    Args:
        item: 원본 항목 문자열.

    Returns:
        정규화된 가맹점명. 매칭 실패 시 입력 그대로.

    Examples:
        >>> normalize_merchant("(일시불)06/20 카페63도")
        '카페63도'
        >>> normalize_merchant("(일시불)05/31 18:28 홈플러스익스")
        '홈플러스익스'
        >>> normalize_merchant("(할부3개월)06/03 20:52 (주)이마트")
        '이마트'
        >>> normalize_merchant("식재료")
        '식재료'
    """
    if not item:
        return item

    match = _SMS_MERCHANT_PATTERN.match(item)
    if not match:
        # PLAIN/OLD/잔액 행 등 SMS 포맷이 아니면 변경하지 않는다.
        return item

    merchant = match.group(1)
    merchant = _CORPORATE_FORM_PATTERN.sub("", merchant)
    merchant = _WHITESPACE_PATTERN.sub(" ", merchant).strip()
    return merchant


class ParseSMSService:
    """
    카드사 결제 문자(SMS)를 파싱하여 구조화된 데이터를 반환합니다.

    Usage:
        result = ParseSMSService(message).parse()
        # result = {"amount": 2400, "item": "세븐일레븐", "payment_method": "신한Big카드", "spent_at": "04/20"}
    """

    def __init__(self, message: str):
        self.message = message

    def is_cancellation(self) -> bool:
        """승인취소 문자인지 판별합니다.

        취소 문자도 금액과 가맹점 형식이 승인 문자와 같아서, 그대로 파싱하면
        환불이 지출로 한 번 더 기록됩니다.
        """
        return bool(_CANCELLATION_PATTERN.search(self.message))

    def parse(self, enum_representation: Literal["label", "value"] = "label") -> dict:
        """
        카드사를 자동 감지하여 문자를 파싱합니다.

        Returns:
            {"amount": int, "item": str, "payment_method": str, "spent_at": str}
            외화 해외승인 문자는 amount가 None이고 "foreign_amount"(Decimal),
            "currency"(ISO 코드)가 추가된다. 환산은 record_card_payment가 한다.

        Raises:
            ValueError: 파싱 실패 또는 지원하지 않는 카드사
        """
        if "[Web발신]\n신한카드" in self.message or "신한(" in self.message:
            return self._parse_shinhan(enum_representation=enum_representation)
        if "[Web발신]\n우리" in self.message:
            return self._parse_woori(enum_representation=enum_representation)
        raise ValueError(ParseSMSErrorMessages.UNSUPPORTED_COMPANY)

    # ------------------------------------------------------------------
    # 카드사별 파서
    # ------------------------------------------------------------------

    def _parse_shinhan(
        self,
        enum_representation: Literal["label", "value"] = "value",
    ) -> dict:
        spent_at = self._extract_spent_at()
        payment_method = getattr(
            ExpensePaymentMethodEnum.SHINHAN,
            enum_representation,
        )

        # 패턴 1: "신한카드(xxxx)승인 ..." 형식
        if "신한카드" in self.message:
            amount, matched_text = self._extract_amount(r"\s([\d,]+)원")

            splits = self.message.split(matched_text, 1)
            if len(splits) < 2:
                raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

            location = splits[1].strip()

            idx = location.find("누적")
            if idx != -1:
                location = location[:idx].strip()

            location = normalize_merchant(location)

            return self._build_result(amount, location, payment_method, spent_at)

        # 패턴 3: "신한(xxxx)해외승인 ... KRW 37,730 (US)MM/DD HH:MM 가맹점 누적..." 형식
        # "신한("을 포함하므로 패턴 2보다 먼저 검사해야 한다.
        if _SHINHAN_OVERSEAS_PATTERN.search(self.message):
            location_match = _SHINHAN_OVERSEAS_LOCATION_PATTERN.search(self.message)
            location = location_match.group(1).strip() if location_match else ""

            krw_match = _SHINHAN_OVERSEAS_AMOUNT_PATTERN.search(self.message)
            if krw_match:
                amount = int(krw_match.group(1).replace(",", ""))
                return self._build_result(amount, location, payment_method, spent_at)

            foreign_match = _SHINHAN_OVERSEAS_FOREIGN_AMOUNT_PATTERN.search(self.message)
            if not foreign_match:
                raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)
            # 원화 금액(amount)은 기록 단계에서 환율로 환산해 채운다.
            result = self._build_result(None, location, payment_method, spent_at)
            result["foreign_amount"] = Decimal(foreign_match.group(1).replace(",", ""))
            result["currency"] = _FOREIGN_CURRENCY_CODES[foreign_match.group(2)]
            return result

        # 패턴 2: "신한(xxxx)승인 ..." 형식 (민생회복 등)
        if "신한(" in self.message:
            amount, _ = self._extract_amount(r"\s([\d,]+)원")

            location_match = _SHINHAN_PAREN_LOCATION_PATTERN.search(self.message)
            location = location_match.group(1).strip() if location_match else ""
            location = normalize_merchant(location)

            return self._build_result(amount, location, payment_method, spent_at)

        raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

    def _parse_woori(
        self,
        enum_representation: Literal["label", "value"] = "value",
    ) -> dict:
        spent_at = self._extract_spent_at()

        payment_method = getattr(
            ExpensePaymentMethodEnum.WOORI,
            enum_representation,
        )

        match = re.search(r"([\d,]+)원", self.message)
        if not match:
            raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

        amount = int(match.group(1).replace(",", ""))

        lines = [line for line in self.message.strip().splitlines() if line.strip()]
        if len(lines) < 5:
            raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

        location = normalize_merchant(lines[-2].strip())

        return self._build_result(amount, location, payment_method, spent_at)

    # ------------------------------------------------------------------
    # 공통 헬퍼
    # ------------------------------------------------------------------

    def _extract_amount(self, pattern: str) -> tuple[int, str]:
        """정규식 패턴으로 금액(int)과 매칭된 문자열을 반환합니다."""
        match = re.search(pattern, self.message)
        if not match:
            raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)
        try:
            amount = int(match.group(1).replace(",", ""))
        except ValueError:
            raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)
        return amount, match.group(0)

    def _extract_spent_at(self) -> str:
        """MM/DD HH:MM 패턴에서 MM/DD를 추출합니다."""
        match = re.search(r"(\d{2}/\d{2})\s+\d{2}:\d{2}", self.message)
        return match.group(1) if match else ""

    @staticmethod
    def _build_result(
        amount: int | None, item: str, payment_method: str, spent_at: str
    ) -> dict:
        item = item.strip()
        if not item:
            raise ValueError(ParseSMSErrorMessages.EMPTY_ITEM)
        item = item[:ITEM_MAX_LENGTH]
        return {
            "amount": amount,
            "item": item,
            "payment_method": payment_method,
            "spent_at": spent_at,
        }
