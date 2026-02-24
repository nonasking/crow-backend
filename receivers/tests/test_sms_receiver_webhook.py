from unittest.mock import patch

import pytest
from rest_framework import status


def test_webhook_api_responds_woori(client):
    with patch(
        "receivers.externals.notion.api_client.NotionClient.create_card_record"
    ) as mock_create:
        mock_create.return_value = None

        url = "/receivers/webhook/"
        message = """[Web발신]
우리 02/23 11:32
*746546
출금 900원
SMS수수료
잔액 41,903,664원"""
        payload = {"message": message}

        response = client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK


def test_webhook_api_responds_shinhan(client):
    with patch(
        "receivers.externals.notion.api_client.NotionClient.create_card_record"
    ) as mock_create:
        mock_create.return_value = None

        url = "/receivers/webhook/"
        message = """[Web발신]
신한카드(4557)승인 강*성 2,400원(일시불)02/23 16:56 세븐일레븐영 누적1,427,265원"""
        payload = {"message": message}

        response = client.post(url, data=payload, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK


def test_webhook_invalid_data(client):
    """
    잘못된 데이터를 보냈을 때 정의한 에러 메시지가 오는지 확인합니다.
    """
    url = "/receivers/webhook/"
    payload = {"wrong_key": "data"}  # 'message' 키가 없음

    response = client.post(url, data=payload, content_type="application/json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.data
