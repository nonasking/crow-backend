"""SMS 웹훅 공유 토큰 검증, 승인취소 무시, 기록 실패 시 응답/롤백 테스트."""

from unittest.mock import patch

import pytest
from django.core.checks import run_checks
from django.db import DatabaseError
from rest_framework import status

from expenses.models import Expense
from receivers.throttling import SMSWebhookThrottle

URL = "/receivers/webhook/"
NOTION_CREATE = "receivers.externals.notion.api_client.NotionClient.create_card_record"
SHINHAN_MESSAGE = (
    "[Web발신]\n"
    "신한카드(4557)승인 강*성 2,400원(일시불)02/23 16:56 세븐일레븐영 누적1,427,265원"
)
SHINHAN_CANCEL_MESSAGE = (
    "[Web발신]\n"
    "신한카드(4557)승인취소 강*성 2,400원(일시불)02/23 16:56 세븐일레븐영 누적1,424,865원"
)


def _post(client, message=SHINHAN_MESSAGE, **extra):
    return client.post(
        URL, data={"message": message}, content_type="application/json", **extra
    )


@pytest.mark.django_db
class TestWebhookToken:
    def test_no_token_configured_allows_request(self, client, settings):
        settings.SMS_WEBHOOK_TOKEN = ""
        with patch(NOTION_CREATE):
            response = _post(client)
        assert response.status_code == status.HTTP_200_OK

    def test_missing_token_rejected(self, client, settings):
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        with patch(NOTION_CREATE) as mock_create:
            response = _post(client)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_create.assert_not_called()
        assert not Expense.objects.exists()

    def test_wrong_token_rejected(self, client, settings):
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        with patch(NOTION_CREATE):
            response = _post(client, HTTP_X_WEBHOOK_TOKEN="nope")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_header_token_accepted(self, client, settings):
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        with patch(NOTION_CREATE):
            response = _post(client, HTTP_X_WEBHOOK_TOKEN="s3cret")
        assert response.status_code == status.HTTP_200_OK
        assert Expense.objects.count() == 1

    def test_query_token_accepted(self, client, settings):
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        with patch(NOTION_CREATE):
            response = client.post(
                f"{URL}?token=s3cret",
                data={"message": SHINHAN_MESSAGE},
                content_type="application/json",
            )
        assert response.status_code == status.HTTP_200_OK

    def test_jwt_header_not_required(self, client, settings):
        """포워더가 이상한 Authorization 헤더를 보내도 JWT 인증 실패로 막히지 않는다."""
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        with patch(NOTION_CREATE):
            response = _post(
                client,
                HTTP_X_WEBHOOK_TOKEN="s3cret",
                HTTP_AUTHORIZATION="Bearer not-a-jwt",
            )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestWebhookCancellation:
    def test_cancellation_ignored(self, client):
        with patch(NOTION_CREATE) as mock_create:
            response = _post(client, message=SHINHAN_CANCEL_MESSAGE)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ignored"
        mock_create.assert_not_called()
        assert not Expense.objects.exists()


@pytest.mark.django_db
class TestWebhookFailures:
    def test_notion_failure_returns_503_and_rolls_back(self, client):
        with patch(NOTION_CREATE, side_effect=RuntimeError("down")):
            response = _post(client)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert not Expense.objects.exists()

    def test_db_failure_skips_notion(self, client):
        with (
            patch(NOTION_CREATE) as mock_create,
            patch.object(Expense.objects, "create", side_effect=DatabaseError("boom")),
        ):
            with pytest.raises(DatabaseError):
                _post(client)
        mock_create.assert_not_called()


@pytest.fixture
def two_per_minute():
    # SimpleRateThrottle은 rate 설정을 클래스 속성으로 들고 있으므로 직접 바꾼다.
    with patch.object(SMSWebhookThrottle, "THROTTLE_RATES", {"sms_webhook": "2/minute"}):
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures("two_per_minute")
class TestWebhookThrottle:
    def test_throttled_after_rate_limit(self, client):
        with patch(NOTION_CREATE):
            codes = [_post(client).status_code for _ in range(3)]
        assert codes == [
            status.HTTP_200_OK,
            status.HTTP_200_OK,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]

    def test_spoofed_forwarded_for_does_not_bypass(self, client):
        """X-Forwarded-For를 매번 바꿔도 같은 버킷을 쓴다."""
        with patch(NOTION_CREATE):
            codes = [
                _post(client, HTTP_X_FORWARDED_FOR=f"1.2.3.{i}, 10.0.0.1").status_code
                for i in range(3)
            ]
        assert codes[2] == status.HTTP_429_TOO_MANY_REQUESTS

    def test_wrong_token_guesses_are_throttled(self, client, settings):
        """권한 검사보다 throttle이 먼저라 토큰 추측도 한도에 걸린다."""
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        codes = [
            _post(client, HTTP_X_WEBHOOK_TOKEN=f"guess-{i}").status_code
            for i in range(3)
        ]
        assert codes == [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]


class TestWebhookTokenSystemCheck:
    def test_warns_when_token_missing_in_production(self, settings):
        settings.DEBUG = False
        settings.SMS_WEBHOOK_TOKEN = ""
        ids = [m.id for m in run_checks()]
        assert "receivers.W001" in ids

    def test_silent_when_token_set(self, settings):
        settings.DEBUG = False
        settings.SMS_WEBHOOK_TOKEN = "s3cret"
        ids = [m.id for m in run_checks()]
        assert "receivers.W001" not in ids
