"""POST /auth/refresh/ — refresh 토큰으로 access 갱신."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

URL = "/auth/refresh/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


def _post(client, body, **extra):
    return client.post(URL, body, content_type="application/json", **extra)


@pytest.mark.django_db
class TestTokenRefresh:
    def test_valid_refresh_returns_usable_access(self, client, user):
        refresh = RefreshToken.for_user(user)

        response = _post(client, {"refresh": str(refresh)})

        assert response.status_code == status.HTTP_200_OK
        access = response.data["access"]
        me = client.get("/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
        assert me.status_code == status.HTTP_200_OK

    def test_refresh_is_not_rotated(self, client, user):
        response = _post(client, {"refresh": str(RefreshToken.for_user(user))})
        assert "refresh" not in response.data

    def test_invalid_refresh_is_401(self, client):
        response = _post(client, {"refresh": "not-a-token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_token_cannot_be_used_as_refresh(self, client, user):
        access = str(RefreshToken.for_user(user).access_token)
        response = _post(client, {"refresh": access})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_refresh_is_400(self, client):
        assert _post(client, {}).status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_access_header_does_not_block_refresh(self, client, user):
        """만료·위조된 Authorization 헤더가 붙어 와도 refresh는 헤더를 보지 않는다."""
        response = _post(
            client,
            {"refresh": str(RefreshToken.for_user(user))},
            HTTP_AUTHORIZATION="Bearer expired.or.garbage",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_inactive_user_refresh_is_rejected(self, client, user):
        refresh = str(RefreshToken.for_user(user))
        user.is_active = False
        user.save()

        response = _post(client, {"refresh": refresh})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
