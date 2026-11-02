import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture(autouse=True)
def _no_webhook_token_by_default(settings):
    """로컬 .env에 SMS_WEBHOOK_TOKEN이 있어도 테스트는 토큰 없는 상태에서 시작한다.

    토큰 검증 테스트는 settings.SMS_WEBHOOK_TOKEN을 직접 설정한다.
    """
    settings.SMS_WEBHOOK_TOKEN = ""


@pytest.fixture(autouse=True)
def _clear_cache():
    """throttle 카운트가 테스트 사이에 이어지지 않게 캐시를 비운다."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def auth_client(user):
    """인증된 API 클라이언트"""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client
