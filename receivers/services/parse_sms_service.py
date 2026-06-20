"""
receivers/services.py

카드사 결제 문자를 파싱하는 서비스 클래스.
"""

import re
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
    merchant = re.sub(r"\s+", " ", merchant).strip()
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

    def parse(self, enum_representation: Literal["label", "value"] = "label") -> dict:
        """
        카드사를 자동 감지하여 문자를 파싱합니다.

        Returns:
            {"amount": int, "item": str, "payment_method": str, "spent_at": str}

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

        # 패턴 2: "신한(xxxx)승인 ..." 형식 (민생회복 등)
        if "신한(" in self.message:
            amount, _ = self._extract_amount(r"\s([\d,]+)원")

            location_match = re.search(r"\d{2}:\d{2}\s+([^잔액]+)", self.message)
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
        amount: int, item: str, payment_method: str, spent_at: str
    ) -> dict:
        return {
            "amount": amount,
            "item": item,
            "payment_method": payment_method,
            "spent_at": spent_at,
        }
