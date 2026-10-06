from datetime import date
from typing import Optional

import requests
from django.conf import settings

from expenses.constants import (
    DEFAULT_EXPENSE_CATEGORY,
    DEFAULT_EXPENSE_SUBCATEGORY,
    ExpenseCategoryEnum,
    ExpensePaymentMethodEnum,
    ExpenseSubCategoryEnum,
)
from expenses.models import Budget, Expense

NOTION_API_URL = settings.NOTION_API_URL
NOTION_EXPENSE_DATABASE_ID = settings.NOTION_EXPENSE_DATABASE_ID
NOTION_EXPENSE_DB_QUERY_URL = settings.NOTION_EXPENSE_DB_QUERY_URL
NOTION_BUDGET_DB_QUERY_URL = settings.NOTION_BUDGET_DB_QUERY_URL


def _format_spent_at(spent_at: Optional[str]) -> str:
    """
    MM/DD 형식을 YYYY-MM-DD 로 변환합니다.
    빈 문자열이거나 파싱 실패 시 오늘 날짜를 반환합니다.
    """
    if not spent_at:
        return date.today().isoformat()
    parts = spent_at.split("/")
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
        version: Optional[str] = None,
    ):
        self.token = token or settings.NOTION_TOKEN
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
        amount, item, payment_method, spent_at = (
            parse_result.get("amount"),
            parse_result.get("item"),
            parse_result.get("payment_method"),
            parse_result.get("spent_at"),
        )
        formatted_date = _format_spent_at(spent_at)
        payload = {
            "parent": {"database_id": NOTION_EXPENSE_DATABASE_ID},
            "properties": {
                "항목": {"title": [{"text": {"content": item}}]},
                "소분류": {"select": {"name": DEFAULT_EXPENSE_SUBCATEGORY.label}},
                "결제방식": {"select": {"name": payment_method}},
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

    def _fetch_all_pages(self, url) -> list[dict]:
        pages = []
        payload: dict = {"page_size": 100}

        while True:
            try:
                response = requests.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=30,
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
        category_label = _select_name(props, "대분류")
        category = _label_to_enum_value(
            category_label,
            ExpenseCategoryEnum,
            DEFAULT_EXPENSE_CATEGORY,
        )

        # ── 소분류 (select) → ExpenseSubCategoryEnum ──
        sub_label = _select_name(props, "소분류")
        sub_category = _label_to_enum_value(
            sub_label,
            ExpenseSubCategoryEnum,
            DEFAULT_EXPENSE_SUBCATEGORY,
        )

        # ── 결제방식 (select) → ExpensePaymentMethodEnum
        payment_label = _select_name(props, "결제방식")
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

    @staticmethod
    def _parse_page_to_budget_data(page: dict) -> Optional[dict]:
        """
        Notion 페이지 객체를 Budget 모델 생성에 필요한 dict로 변환합니다.

        Notion 필드 → Budget 필드 매핑:
            연도(number)     → year
            월(number)       → month
            대분류(select)   → category      (enum value 변환)
            소분류(select)   → sub_category  (enum value 변환)
            예산(number)     → amount
            비고(rich_text)  → memo

        Returns:
            Budget 생성용 dict, 필수 필드(연도/월) 누락 시 None
        """
        props = page.get("properties", {})

        # ── 연도 (number) ─────────────────────────────
        year = props.get("연도", {}).get("number")
        if not year:
            return None

        # ── 월 (number) ───────────────────────────────
        month = props.get("월", {}).get("number")
        if not month or not (1 <= month <= 12):
            return None

        # ── 대분류 (select) → ExpenseCategoryEnum ─────
        category_label = _select_name(props, "대분류")
        category = _label_to_enum_value(
            category_label,
            ExpenseCategoryEnum,
            DEFAULT_EXPENSE_CATEGORY,
        )

        # ── 소분류 (select) → ExpenseSubCategoryEnum ──
        sub_label = _select_name(props, "소분류")
        sub_category = _label_to_enum_value(
            sub_label,
            ExpenseSubCategoryEnum,
            DEFAULT_EXPENSE_SUBCATEGORY,
        )

        # ── 예산 (number) ─────────────────────────────
        amount = props.get("예산", {}).get("number") or 0

        # ── 비고 (rich_text) ──────────────────────────
        memo_list = props.get("비고", {}).get("title", [])
        memo = memo_list[0]["text"]["content"] if memo_list else ""

        return {
            "year": int(year),
            "month": int(month),
            "category": category,
            "sub_category": sub_category,
            "amount": amount,
            "memo": memo,
        }

    def migrate_budget_to_db(
        self,
        skip_duplicates: bool = True,
        batch_size: int = 100,
    ) -> dict:
        """
        Notion 예산 데이터베이스의 모든 레코드를 Django DB(Budget 모델)로 마이그레이션합니다.

        Args:
            skip_duplicates:    True면 (year, month, category, sub_category) 조합이
                                이미 DB에 존재하는 경우 건너뜁니다. (기본값 True)
            batch_size:         bulk_create 단위 크기.

        Returns:
            {
                "total": int,
                "created": int,
                "skipped": int,
                "errors": list[str]
            }
        """
        return self._migrate_pages_to_db(
            url=NOTION_BUDGET_DB_QUERY_URL,
            model=Budget,
            parse_page=self._parse_page_to_budget_data,
            duplicate_fields=("year", "month", "category", "sub_category"),
            skip_duplicates=skip_duplicates,
            batch_size=batch_size,
        )

    def migrate_expense_to_db(
        self,
        skip_duplicates: bool = False,
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
        return self._migrate_pages_to_db(
            url=NOTION_EXPENSE_DB_QUERY_URL,
            model=Expense,
            parse_page=self._parse_page_to_expense_data,
            duplicate_fields=("spent_at", "item", "amount"),
            skip_duplicates=skip_duplicates,
            batch_size=batch_size,
        )

    def _migrate_pages_to_db(
        self,
        url: str,
        model,
        parse_page,
        duplicate_fields: tuple[str, ...],
        skip_duplicates: bool,
        batch_size: int,
    ) -> dict:
        pages = self._fetch_all_pages(url=url)

        # 페이지마다 exists() 쿼리를 날리지 않도록 기존 키를 한 번에 읽어 둔다.
        existing_keys = (
            {
                tuple(_as_lookup_value(v) for v in row)
                for row in model.objects.values_list(*duplicate_fields)
            }
            if skip_duplicates
            else set()
        )

        to_create = []
        skipped = 0
        errors: list[str] = []

        for page in pages:
            data = parse_page(page)

            if data is None:
                errors.append(page.get("id", "unknown"))
                skipped += 1
                continue

            key = tuple(_as_lookup_value(data[f]) for f in duplicate_fields)
            if key in existing_keys:
                skipped += 1
                continue

            to_create.append(model(**data))

        model.objects.bulk_create(to_create, batch_size=batch_size)

        return {
            "total": len(pages),
            "created": len(to_create),
            "skipped": skipped,
            "errors": errors,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────


def _as_lookup_value(value):
    """DB 값과 Notion 파싱 값을 같은 형태로 비교하기 위한 정규화.

    - date → ISO 문자열 (Notion 날짜는 문자열로 들어온다)
    - float → int (Notion number는 float일 수 있고, IntegerField 조회 시 int로 변환된다)
    """
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return int(value)
    return value


def _select_name(props: dict, key: str) -> str:
    """Notion select 속성의 name 값. 값이 비어 있으면 빈 문자열."""
    return (props.get(key, {}).get("select") or {}).get("name", "")


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
