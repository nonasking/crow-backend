from unittest.mock import patch

import pytest
from rest_framework import status


def test_health(client):
    url = "/health/"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
