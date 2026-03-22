import pytest
from django.contrib.auth.models import User
from rest_framework import status


@pytest.mark.django_db
def test_login_success(client):
    User.objects.create_user(username="testuser", password="testpass123")

    response = client.post(
        "/auth/login/",
        {"username": "testuser", "password": "testpass123"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["user"]["username"] == "testuser"


@pytest.mark.django_db
def test_login_wrong_password(client):
    User.objects.create_user(username="testuser", password="testpass123")

    response = client.post(
        "/auth/login/",
        {"username": "testuser", "password": "wrongpassword"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.data


@pytest.mark.django_db
def test_login_missing_fields(client):
    response = client.post(
        "/auth/login/",
        {"username": "testuser"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_me_authenticated(auth_client):
    response = auth_client.get("/auth/me/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "testuser"


@pytest.mark.django_db
def test_me_unauthenticated(client):
    response = client.get("/auth/me/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_logout_authenticated(auth_client):
    response = auth_client.post("/auth/logout/")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_logout_unauthenticated(client):
    response = client.post("/auth/logout/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
