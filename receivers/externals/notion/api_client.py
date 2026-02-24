from datetime import date
from typing import Optional

import requests
from django.conf import settings

from expenses.constants import DEFAULT_EXPENSE_CATEGORY, DEFAULT_EXPENSE_SUBCATEGORY

NOTION_API_URL = "https://api.notion.com/v1/pages"


def _format_payment_date(payment_date: Optional[str]) -> str:
    """
    MM/DD 형식을 YYYY-MM-DD 로 변환합니다.
    빈 문자열이거나 파싱 실패 시 오늘 날짜를 반환합니다.
    """
    if not payment_date:
        return date.today().isoformat()

    parts = payment_date.split("/")
    if len(parts) != 2:
        return date.today().isoformat()

    try:
        month, day = int(parts[0]), int(parts[1])
        return date(date.today().year, month, day).isoformat()
    except ValueError:
        return date.today().isoformat()


class NotionClient:
    """Notion API와 통신하는 클라이언트."""

    def __init__(
        self,
        token: Optional[str] = None,
        database_id: Optional[str] = None,
        version: Optional[str] = None,
    ):
        self.token = token or settings.NOTION_TOKEN
        self.database_id = database_id or settings.NOTION_DATABASE_ID
        self.version = version or settings.NOTION_VERSION

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.version,
            "Content-Type": "application/json",
        }

    def create_card_record(
        self,
        parse_result: dict,
    ) -> None:
        """
        카드 결제 정보를 Notion 데이터베이스에 새 페이지로 생성합니다.

        Raises:
            RuntimeError: Notion API 요청 실패 시
        """
        amount, place, card_company, payment_date = (
            parse_result.get("amount"),
            parse_result.get("place"),
            parse_result.get("card_company"),
            parse_result.get("payment_date"),
        )

        formatted_date = _format_payment_date(payment_date)

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "항목": {"title": [{"text": {"content": place}}]},
                "소분류": {"select": {"name": DEFAULT_EXPENSE_SUBCATEGORY.label}},
                "결제방식": {"select": {"name": card_company}},
                "날짜": {"date": {"start": formatted_date}},
                "수입": {"number": 0},
                "지출": {"number": amount},
                "대분류": {"select": {"name": DEFAULT_EXPENSE_CATEGORY.label}},
                "비고": {"rich_text": [{"text": {"content": ""}}]},
            },
        }

        try:
            response = requests.post(
                NOTION_API_URL,
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Notion API 요청 실패: {e}") from e

        if response.status_code >= 400:
            raise RuntimeError(f"Notion 응답 코드: {response.status_code}")
