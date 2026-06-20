"""preview_item_cleanup management command 테스트.

dry-run 이므로: 변경 건수/샘플 정확성 + DB 절대 미변경 을 검증한다.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from expenses.models import Expense


def _make(item):
    return Expense.objects.create(
        spent_at="2024-06-20",
        category="ETC",
        sub_category="ETC",
        item=item,
        payment_method="SHINHAN",
        amount=1000,
    )


@pytest.mark.django_db
class TestPreviewItemCleanupCommand:

    def _run(self, *args):
        out = StringIO()
        call_command("preview_item_cleanup", *args, stdout=out)
        return out.getvalue()

    def test_reports_correct_change_count(self):
        # 변경 대상 3건
        _make("(일시불)06/20 카페63도")
        _make("(할부3개월)06/03 20:52 (주)이마트")
        _make("(일시불)05/31 18:28 홈플러스익스")
        # 후보지만 비매칭 1건 ('(' 시작이나 SMS 포맷 아님)
        _make("(주)이마트")
        # 후보 아님 2건
        _make("식재료")
        _make("잔액 2,311,720원")

        output = self._run()

        # 후보(item이 '(' 로 시작) = 4건
        assert "후보(item이 '('로 시작): 4건" in output
        # 실제 변경 대상 = 3건
        assert "실제 변경 대상: 3건" in output

    def test_sample_shows_before_after(self):
        _make("(일시불)06/20 카페63도")
        output = self._run()
        assert "'(일시불)06/20 카페63도'" in output
        assert "'카페63도'" in output
        assert "->" in output

    def test_does_not_mutate_db(self):
        ids = [
            _make("(일시불)06/20 카페63도").id,
            _make("식재료").id,
        ]
        before = dict(
            Expense.objects.filter(id__in=ids).values_list("id", "item")
        )

        self._run()

        after = dict(
            Expense.objects.filter(id__in=ids).values_list("id", "item")
        )
        # dry-run: 원본 item 그대로
        assert before == after
        assert after[ids[0]] == "(일시불)06/20 카페63도"

    def test_no_changes_message(self):
        _make("식재료")  # 후보 아님
        output = self._run()
        assert "실제 변경 대상: 0건" in output
        assert "변경할 항목이 없습니다." in output

    def test_limit_option_truncates_sample(self):
        for i in range(5):
            _make(f"(일시불)06/2{i} 가맹점{i}")
        output = self._run("--limit", "2")
        # 샘플 헤더에 2/5 표기
        assert "변경 샘플 (2/5건)" in output
        assert "외 3건" in output

    def test_all_option_shows_everything(self):
        for i in range(5):
            _make(f"(일시불)06/2{i} 가맹점{i}")
        output = self._run("--all")
        assert "변경 샘플 (5/5건)" in output
        # --all 이면 "외 N건" 안내 없음
        assert "외 " not in output
