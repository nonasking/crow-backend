"""
receivers/services.py

카드사 결제 문자를 파싱하는 서비스 클래스.
"""

import re

from expenses.constants import ExpensePaymentMethodEnum
from receivers.constants import ParseSMSErrorMessages


class ParseSMSService:
    """
    카드사 결제 문자(SMS)를 파싱하여 구조화된 데이터를 반환합니다.

    Usage:
        result = ParseSMSService(message).parse()
        # result = {"amount": 2400, "place": "세븐일레븐", "card_company": "신한Big카드", "payment_date": "04/20"}
    """

    def __init__(self, message: str):
        self.message = message

    def parse(self) -> dict:
        """
        카드사를 자동 감지하여 문자를 파싱합니다.

        Returns:
            {"amount": int, "place": str, "card_company": str, "payment_date": str}

        Raises:
            ValueError: 파싱 실패 또는 지원하지 않는 카드사
        """
        if "[Web발신]\n신한카드" in self.message or "신한(" in self.message:
            return self._parse_shinhan()
        if "[Web발신]\n우리" in self.message:
            return self._parse_woori()
        raise ValueError(ParseSMSErrorMessages.UNSUPPORTED_COMPANY)

    # ------------------------------------------------------------------
    # 카드사별 파서
    # ------------------------------------------------------------------

    def _parse_shinhan(self) -> dict:
        payment_date = self._extract_payment_date()

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

            location = re.sub(r"\d{2}:\d{2}\s+", "", location).strip()

            return self._build_result(
                amount, location, ExpensePaymentMethodEnum.SHINHAN.label, payment_date
            )

        # 패턴 2: "신한(xxxx)승인 ..." 형식 (민생회복 등)
        if "신한(" in self.message:
            amount, _ = self._extract_amount(r"\s([\d,]+)원")

            location_match = re.search(r"\d{2}:\d{2}\s+([^잔액]+)", self.message)
            location = location_match.group(1).strip() if location_match else ""

            return self._build_result(
                amount, location, ExpensePaymentMethodEnum.SHINHAN.label, payment_date
            )

        raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

    def _parse_woori(self) -> dict:
        payment_date = self._extract_payment_date()

        match = re.search(r"([\d,]+)원", self.message)
        if not match:
            raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

        amount = int(match.group(1).replace(",", ""))

        lines = [line for line in self.message.strip().splitlines() if line.strip()]
        if len(lines) < 5:
            raise ValueError(ParseSMSErrorMessages.INVALID_FORMAT)

        location = lines[-2].strip()

        return self._build_result(
            amount, location, ExpensePaymentMethodEnum.WOORI.label, payment_date
        )

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

    def _extract_payment_date(self) -> str:
        """MM/DD HH:MM 패턴에서 MM/DD를 추출합니다."""
        match = re.search(r"(\d{2}/\d{2})\s+\d{2}:\d{2}", self.message)
        return match.group(1) if match else ""

    @staticmethod
    def _build_result(
        amount: int, place: str, card_company: str, payment_date: str
    ) -> dict:
        return {
            "amount": amount,
            "place": place,
            "card_company": card_company,
            "payment_date": payment_date,
        }
