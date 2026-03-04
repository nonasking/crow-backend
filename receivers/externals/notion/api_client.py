from datetime import date
from typing import Optional

import requests
from django.conf import settings

from expenses.constants import DEFAULT_EXPENSE_CATEGORY, DEFAULT_EXPENSE_SUBCATEGORY

NOTION_API_URL = settings.NOTION_API_URL
NOTION_DB_QUERY_URL = settings.NOTION_DB_QUERY_URL


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

    # ──────────────────────────────────────────────
    # Notion → DB 마이그레이션
    # ──────────────────────────────────────────────

    def _fetch_all_pages(self) -> list[dict]:
        url = NOTION_DB_QUERY_URL.format(database_id=self.database_id)
        pages = []
        payload: dict = {"page_size": 100}  # 명시적으로 최대치 지정

        while True:
            try:
                response = requests.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=30,  # 10 → 30으로 늘리기
                )
            except requests.RequestException as e:
                raise RuntimeError(f"Notion API 요청 실패: {e}") from e

            if response.status_code >= 400:
                raise RuntimeError(f"Notion 응답 코드: {response.status_code}")

            data = response.json()
            pages.extend(data.get("results", []))

            if not data.get("has_more"):
                break

            payload = {"page_size": 100, "start_cursor": data["next_cursor"]}

        return pages

    @staticmethod
    def _parse_page_to_expense_data(page: dict) -> Optional[dict]:
        """
        Notion 페이지 객체를 Expense 모델 생성에 필요한 dict로 변환합니다.

        Notion 필드 → Expense 필드 매핑:
            항목(title)      → item
            소분류(select)   → sub_category  (enum value 변환)
            결제방식(select) → payment_method (enum value 변환)
            날짜(date)       → spent_at
            지출(number)     → amount
            대분류(select)   → category      (enum value 변환)
            비고(rich_text)  → memo

        Returns:
            Expense 생성용 dict, 필수 필드 누락 시 None
        """
        from expenses.constants import (
            ExpenseCategoryEnum,
            ExpensePaymentMethodEnum,
            ExpenseSubCategoryEnum,
        )

        props = page.get("properties", {})

        # ── 항목 (title) ──────────────────────────────
        title_list = props.get("항목", {}).get("title", [])
        item = title_list[0]["text"]["content"] if title_list else ""

        # ── 날짜 (date) ───────────────────────────────
        date_obj = props.get("날짜", {}).get("date")
        if not date_obj or not date_obj.get("start"):
            return None  # 날짜 없는 레코드는 건너뜀
        spent_at = date_obj["start"]  # 이미 YYYY-MM-DD 형식

        # ── 지출 (number) ─────────────────────────────
        amount = props.get("지출", {}).get("number") or 0

        # ── 대분류 (select) → ExpenseCategoryEnum ─────
        category_label = (props.get("대분류", {}).get("select") or {}).get("name", "")
        category = _label_to_enum_value(
            category_label,
            ExpenseCategoryEnum,
            DEFAULT_EXPENSE_CATEGORY,
        )

        # ── 소분류 (select) → ExpenseSubCategoryEnum ──
        sub_label = (props.get("소분류", {}).get("select") or {}).get("name", "")
        sub_category = _label_to_enum_value(
            sub_label,
            ExpenseSubCategoryEnum,
            DEFAULT_EXPENSE_SUBCATEGORY,
        )

        # ── 결제방식 (select) → ExpensePaymentMethodEnum
        payment_label = (props.get("결제방식", {}).get("select") or {}).get("name", "")
        payment_method = _label_to_enum_value(
            payment_label,
            ExpensePaymentMethodEnum,
            ExpensePaymentMethodEnum.ETC,  # 매핑 실패 시 기본값
        )

        # ── 비고 (rich_text) ──────────────────────────
        memo_list = props.get("비고", {}).get("rich_text", [])
        memo = memo_list[0]["text"]["content"] if memo_list else ""

        return {
            "spent_at": spent_at,
            "category": category,
            "sub_category": sub_category,
            "item": item,
            "payment_method": payment_method,
            "amount": amount,
            "memo": memo,
        }

    def migrate_to_db(
        self,
        skip_duplicates: bool = True,
        batch_size: int = 100,
    ) -> dict:
        """
        Notion 데이터베이스의 모든 레코드를 Django DB(Expense 모델)로 마이그레이션합니다.

        Args:
            skip_duplicates: True면 이미 DB에 동일 레코드가 있을 경우 건너뜁니다.
                             (spent_at + item + amount 조합으로 중복 판단)
            batch_size:      bulk_create 단위 크기.

        Returns:
            {
                "total": int,       # Notion에서 가져온 전체 페이지 수
                "created": int,     # 새로 생성된 레코드 수
                "skipped": int,     # 건너뛴 레코드 수 (중복 or 파싱 실패)
                "errors": list[str] # 파싱 실패 page_id 목록
            }

        Raises:
            RuntimeError: Notion API 요청 실패 시
        """
        from expenses.models import Expense

        pages = self._fetch_all_pages()
        total = len(pages)

        to_create: list[Expense] = []
        skipped = 0
        errors: list[str] = []

        for page in pages:
            page_id = page.get("id", "unknown")
            data = self._parse_page_to_expense_data(page)

            if data is None:
                errors.append(page_id)
                skipped += 1
                continue

            if (
                skip_duplicates
                and Expense.objects.filter(
                    spent_at=data["spent_at"],
                    item=data["item"],
                    amount=data["amount"],
                ).exists()
            ):
                skipped += 1
                continue

            to_create.append(Expense(**data))

        # bulk_create로 DB 일괄 저장
        created_count = 0
        for i in range(0, len(to_create), batch_size):
            batch = to_create[i : i + batch_size]
            Expense.objects.bulk_create(batch)
            created_count += len(batch)

        return {
            "total": total,
            "created": created_count,
            "skipped": skipped,
            "errors": errors,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────


def _label_to_enum_value(label: str, enum_class, default):
    """
    Notion select 필드의 name(label) 값을 Django Enum의 value로 변환합니다.
    매핑 실패 시 default를 반환합니다.

    예) "식비" → ExpenseCategoryEnum.FOOD.value
    """
    for member in enum_class:
        if member.label == label:
            return member.value
    return default.value
