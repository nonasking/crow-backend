"""UNSETTLED 결정성 기반 자동분류 (배치) 서비스.

과거 **수동 확정분**(category != UNSETTLED AND auto_classified == False)에서
가맹점명(normalize_merchant 키)별로 (category, sub_category) 분포가 단일하고
충분히 반복된 경우만 "결정적인 규칙"으로 학습한다. 그 규칙으로 UNSETTLED
Expense를 매칭한다.

핵심 안전장치:
  - 학습 대상에서 auto_classified=True(자동분류 결과)를 반드시 제외 → 에코 챔버 방지.
  - 변경 대상은 UNSETTLED 행뿐. (적용은 관리 커맨드의 --apply에서 수행.)

normalize_merchant 는 receivers.services 의 단일 진실 공급원을 재사용한다
(절대 재구현하지 않음).
"""

from collections import Counter, defaultdict

from expenses.constants import ExpenseCategoryEnum
from expenses.models import Expense
from receivers.services import normalize_merchant

# 규칙 키로 채택하기 위한 최소 키 길이(1글자 가맹점명은 모호하므로 제외).
MIN_KEY_LENGTH = 2


def build_deterministic_rules(min_count: int = 2) -> dict[str, tuple[str, str]]:
    """수동 확정분 이력에서 결정적인 가맹점 분류 규칙을 학습한다.

    학습 대상은 **수동 확정분만**이다:
        category != UNSETTLED  AND  auto_classified == False
    (자동분류 결과를 다시 학습하면 에코 챔버가 되므로 auto_classified=True는 제외.)

    각 행을 normalize_merchant(item) 키로 그룹화하고, 키별
    (category, sub_category) 분포를 집계한다. 다음을 모두 만족할 때만 규칙으로 채택한다:
        1. 분포가 단일 (category, sub_category)
        2. 등장 횟수 >= min_count
        3. len(key) >= MIN_KEY_LENGTH

    Args:
        min_count: 규칙 채택 최소 등장 횟수 (기본 2).

    Returns:
        { 정규화된_가맹점명: (category, sub_category) } 형태의 규칙 맵.
    """
    training_qs = (
        Expense.objects.exclude(category=ExpenseCategoryEnum.UNSETTLED)
        .filter(auto_classified=False)
        .values_list("item", "category", "sub_category")
    )

    # key -> Counter[(category, sub_category)]
    distribution: dict[str, Counter] = defaultdict(Counter)
    for item, category, sub_category in training_qs.iterator():
        key = normalize_merchant(item)
        if len(key) < MIN_KEY_LENGTH:
            continue
        distribution[key][(category, sub_category)] += 1

    rules: dict[str, tuple[str, str]] = {}
    for key, counter in distribution.items():
        # 분포가 단일 라벨이어야 한다 (모호하면 제외).
        if len(counter) != 1:
            continue
        (label, count), = counter.items()
        if count < min_count:
            continue
        rules[key] = label

    return rules


def classify_unsettled(min_count: int = 2, apply: bool = False) -> dict:
    """UNSETTLED Expense를 학습된 규칙에 매칭한다 (dry-run/apply 공용 로직).

    매칭된 UNSETTLED 행은 규칙의 (category, sub_category)로 분류 후보가 된다.
    apply=True 이면 매칭된 행에 분류값을 set 하고 auto_classified=True 로 표시한 뒤
    bulk_update 로 저장한다. (UNSETTLED 외 행은 어떤 경우에도 변경하지 않는다.)

    매칭 안 되는 UNSETTLED는 두 가지로 구분해 통계를 만든다:
      - "ambiguous": 학습 이력은 있으나 분포가 모호하거나(저빈도 포함) 규칙으로
        채택되지 못한 가맹점.
      - "new": 수동 확정분 이력에 한 번도 등장하지 않은 신규 가맹점.

    Args:
        min_count: 규칙 채택 최소 등장 횟수 (기본 2).
        apply: True면 실제 DB 변경 수행, False면 dry-run(미변경).

    Returns:
        {
            "rules_count": int,            # 학습된 규칙 수
            "total_unsettled": int,        # UNSETTLED 전체 건수
            "matched": [                   # 매칭된 후보 목록
                {"id", "item", "key", "category", "sub_category"}, ...
            ],
            "matched_count": int,
            "unmatched_count": int,
            "ambiguous": Counter,          # key -> 미매칭 UNSETTLED 등장수 (이력 있음)
            "new": Counter,                # key -> 미매칭 UNSETTLED 등장수 (이력 없음)
            "applied": int,                # apply=True일 때 실제 변경 건수, 아니면 0
        }
    """
    rules = build_deterministic_rules(min_count=min_count)

    # 이력에 등장한 적이 있는 키 집합 (ambiguous vs new 구분용).
    seen_keys = _seen_manual_keys()

    unsettled_qs = Expense.objects.filter(category=ExpenseCategoryEnum.UNSETTLED)
    total_unsettled = unsettled_qs.count()

    matched: list[dict] = []
    to_update: list[Expense] = []
    ambiguous: Counter = Counter()
    new: Counter = Counter()

    for expense in unsettled_qs.iterator():
        key = normalize_merchant(expense.item)
        rule = rules.get(key)
        if rule is not None:
            category, sub_category = rule
            matched.append(
                {
                    "id": expense.id,
                    "item": expense.item,
                    "key": key,
                    "category": category,
                    "sub_category": sub_category,
                }
            )
            if apply:
                expense.category = category
                expense.sub_category = sub_category
                expense.auto_classified = True
                to_update.append(expense)
            continue

        # 미매칭: 이력 유무로 모호/신규 구분.
        if key in seen_keys:
            ambiguous[key] += 1
        else:
            new[key] += 1

    applied = 0
    if apply and to_update:
        Expense.objects.bulk_update(
            to_update,
            ["category", "sub_category", "auto_classified"],
            batch_size=500,
        )
        applied = len(to_update)

    return {
        "rules_count": len(rules),
        "total_unsettled": total_unsettled,
        "matched": matched,
        "matched_count": len(matched),
        "unmatched_count": total_unsettled - len(matched),
        "ambiguous": ambiguous,
        "new": new,
        "applied": applied,
    }


def _seen_manual_keys() -> set[str]:
    """수동 확정분 이력에 등장한 정규화 가맹점 키 집합을 반환한다.

    ambiguous(이력 있음) vs new(신규) 구분 기준으로만 사용하므로 min_count/단일성
    조건은 적용하지 않는다 (등장 자체 유무만 판단).
    """
    training_qs = (
        Expense.objects.exclude(category=ExpenseCategoryEnum.UNSETTLED)
        .filter(auto_classified=False)
        .values_list("item", flat=True)
    )
    keys: set[str] = set()
    for item in training_qs.iterator():
        key = normalize_merchant(item)
        if len(key) >= MIN_KEY_LENGTH:
            keys.add(key)
    return keys


def revert_auto_classified() -> int:
    """auto_classified=True 행을 UNSETTLED/UNSETTLED 로 되돌리고 플래그를 해제한다.

    수동분(auto_classified=False)은 절대 변경하지 않는다.

    Returns:
        되돌린 행 수.
    """
    return Expense.objects.filter(auto_classified=True).update(
        category=ExpenseCategoryEnum.UNSETTLED,
        sub_category=ExpenseCategoryEnum.UNSETTLED,
        auto_classified=False,
    )
