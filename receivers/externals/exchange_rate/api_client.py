from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


class ExchangeRateError(RuntimeError):
    """환율 조회 실패. Notion 실패(RuntimeError)와 구분해 응답하기 위해 따로 둔다."""


class ExchangeRateClient:
    """외화 → 원화 환율을 조회하는 클라이언트 (Frankfurter API 형식).

    응답 예: {"amount": 1.0, "base": "USD", "date": "2026-11-11", "rates": {"KRW": 1336.9}}
    """

    def __init__(self, api_url: str | None = None):
        self.api_url = api_url or settings.EXCHANGE_RATE_API_URL

    def get_krw_rate(self, currency: str) -> Decimal:
        """1 `currency`당 원화 금액을 반환합니다.

        Raises:
            ExchangeRateError: 요청 실패, 오류 응답, 응답 형식이 예상과 다를 때
        """
        try:
            response = requests.get(
                self.api_url,
                params={"base": currency, "symbols": "KRW"},
                timeout=10,
            )
        except requests.RequestException as e:
            raise ExchangeRateError(f"환율 API 요청 실패: {e}") from e

        if response.status_code >= 400:
            raise ExchangeRateError(f"환율 API 응답 코드: {response.status_code}")

        try:
            # float을 거치지 않도록 str로 바꿔 Decimal로 만든다.
            rate = Decimal(str(response.json()["rates"]["KRW"]))
        except (ValueError, KeyError, TypeError, InvalidOperation) as e:
            raise ExchangeRateError(f"환율 API 응답 형식 오류: {e}") from e

        if rate <= 0:
            raise ExchangeRateError(f"환율 API 응답 값 오류: {rate}")
        return rate
