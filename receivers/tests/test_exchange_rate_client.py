"""ExchangeRateClient: 응답 파싱과 실패 시 ExchangeRateError 변환."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from receivers.externals.exchange_rate.api_client import (
    ExchangeRateClient,
    ExchangeRateError,
)

REQUESTS_GET = "receivers.externals.exchange_rate.api_client.requests.get"
API_URL = "https://rates.example/v1/latest"


def _response(status_code=200, json_data=None, json_error=None):
    response = MagicMock(status_code=status_code)
    if json_error:
        response.json.side_effect = json_error
    else:
        response.json.return_value = json_data
    return response


def test_returns_krw_rate_as_decimal():
    body = {"amount": 1.0, "base": "USD", "date": "2026-11-11", "rates": {"KRW": 1336.9}}
    with patch(REQUESTS_GET, return_value=_response(json_data=body)) as mock_get:
        rate = ExchangeRateClient(api_url=API_URL).get_krw_rate("USD")

    assert rate == Decimal("1336.9")
    mock_get.assert_called_once_with(
        API_URL, params={"base": "USD", "symbols": "KRW"}, timeout=10
    )


@pytest.mark.parametrize(
    "response",
    [
        _response(status_code=500),
        _response(json_data={"message": "not found"}),
        _response(json_data={"rates": {"KRW": None}}),
        _response(json_data={"rates": {"KRW": 0}}),
        _response(json_error=ValueError("not json")),
    ],
    ids=["http_error", "missing_rates", "null_rate", "zero_rate", "invalid_json"],
)
def test_bad_response_raises(response):
    with patch(REQUESTS_GET, return_value=response):
        with pytest.raises(ExchangeRateError):
            ExchangeRateClient(api_url=API_URL).get_krw_rate("USD")


def test_network_error_raises():
    with patch(REQUESTS_GET, side_effect=requests.ConnectionError("down")):
        with pytest.raises(ExchangeRateError):
            ExchangeRateClient(api_url=API_URL).get_krw_rate("USD")
