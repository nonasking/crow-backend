"""ParseSMSService 파서 회귀 테스트.

normalize_merchant 적용 후 item이 깨끗하게 나오는지 + amount/spent_at/
payment_method 추출에 회귀가 없는지 검증한다.

파서는 expenses.constants(Django)에 의존하므로 DB 마크가 없어도 Django
settings 로딩이 필요하다. 그러나 ORM은 쓰지 않으므로 django_db 마크는 불필요.
"""

import pytest

from expenses.constants import ExpensePaymentMethodEnum
from receivers.services import ParseSMSService


class TestParseShinhanCard:
    """패턴1: '신한카드(xxxx)승인 ...' (누적 절단 포함)."""

    MESSAGE = (
        "[Web발신]\n"
        "신한카드(4557)승인 강*성 2,400원(일시불)02/23 16:56 세븐일레븐영 누적1,427,265원"
    )

    def test_item_normalized(self):
        result = ParseSMSService(self.MESSAGE).parse()
        # 마커/날짜/시간/누적 모두 제거되어 가맹점명만 남아야 함
        assert result["item"] == "세븐일레븐영"

    def test_amount_no_regression(self):
        result = ParseSMSService(self.MESSAGE).parse()
        assert result["amount"] == 2400

    def test_spent_at_no_regression(self):
        result = ParseSMSService(self.MESSAGE).parse()
        assert result["spent_at"] == "02/23"

    def test_payment_method_no_regression(self):
        # 기본 enum_representation="label"
        result = ParseSMSService(self.MESSAGE).parse()
        assert result["payment_method"] == ExpensePaymentMethodEnum.SHINHAN.label

    def test_payment_method_value_representation(self):
        result = ParseSMSService(self.MESSAGE).parse(enum_representation="value")
        assert result["payment_method"] == ExpensePaymentMethodEnum.SHINHAN.value

    def test_halbu_marker_also_stripped(self):
        message = (
            "[Web발신]\n"
            "신한카드(4557)승인 강*성 30,000원(할부3개월)06/03 20:52 (주)이마트 누적500,000원"
        )
        result = ParseSMSService(message).parse()
        assert result["item"] == "이마트"
        assert result["amount"] == 30000
        assert result["spent_at"] == "06/03"


class TestParseShinhanParenBranch:
    """패턴2: '신한(xxxx)승인 ...' 분기 (민생회복 등). normalize는 사실상 no-op."""

    MESSAGE = (
        "[Web발신]\n"
        "신한(1234)승인 강*성 10,000원 06/20 14:30 동네카페 잔액50,000원"
    )

    def test_branch_routed_and_parses(self):
        # '신한(' 가 message에 있으므로 _parse_shinhan 패턴2로 라우팅
        result = ParseSMSService(self.MESSAGE).parse()
        assert result["amount"] == 10000
        assert result["payment_method"] == ExpensePaymentMethodEnum.SHINHAN.label

    def test_item_extracted(self):
        # 패턴2는 'HH:MM 다음 ~ 잔액 전' 을 location으로 잡는다.
        # 이 location은 '(일시불)...' 포맷이 아니라 normalize 미적용(no-op).
        result = ParseSMSService(self.MESSAGE).parse()
        assert result["item"] == "동네카페"


class TestParseWoori:
    """우리 분기: amount/spent_at/payment_method 무회귀 + item 정규화."""

    # 기존 웹훅 테스트와 동일한 비매칭 케이스 (SMS수수료 — normalize no-op)
    PLAIN_MESSAGE = (
        "[Web발신]\n"
        "우리 02/23 11:32\n"
        "*746546\n"
        "출금 900원\n"
        "SMS수수료\n"
        "잔액 41,903,664원"
    )

    def test_plain_item_unchanged(self):
        result = ParseSMSService(self.PLAIN_MESSAGE).parse()
        assert result["item"] == "SMS수수료"

    def test_amount_no_regression(self):
        result = ParseSMSService(self.PLAIN_MESSAGE).parse()
        assert result["amount"] == 900

    def test_payment_method_no_regression(self):
        result = ParseSMSService(self.PLAIN_MESSAGE).parse()
        assert result["payment_method"] == ExpensePaymentMethodEnum.WOORI.label

    def test_woori_item_normalized_when_sms_format(self):
        # lines[-2]가 SMS 마커 포맷이면 normalize 되어야 함.
        message = (
            "[Web발신]\n"
            "우리 06/20 14:30\n"
            "*746546\n"
            "출금 5,000원\n"
            "(일시불)06/20 14:30 (주)이마트\n"
            "잔액 1,000,000원"
        )
        result = ParseSMSService(message).parse()
        assert result["item"] == "이마트"
        assert result["amount"] == 5000


class TestParseUnsupported:
    """지원하지 않는 카드사는 ValueError."""

    def test_unsupported_company_raises(self):
        with pytest.raises(ValueError):
            ParseSMSService("[Web발신]\n국민카드 ...").parse()
