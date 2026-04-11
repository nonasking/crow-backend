---
name: drf-qa
description: "DRF pytest 테스트 작성 및 실행 스킬. crow-backend 프로젝트의 pytest-django 패턴으로 ViewSet, Serializer, Service 레이어 테스트를 작성하고 실제로 실행하여 결과를 검증한다. '테스트 작성', '테스트 추가', 'pytest', '테스트 실행', 'test coverage' 요청 또는 구현 완료 후 검증이 필요할 때 반드시 이 스킬을 사용할 것."
---

# DRF pytest 테스트 스킬

## 1. 테스트 파일 위치 & 명명

```
{app}/tests/
├── __init__.py
├── test_{resource}_viewset.py    # ViewSet 테스트
├── test_{resource}_serializer.py # Serializer 유효성 검사 테스트 (선택)
└── test_{domain}_service.py      # Service 로직 테스트 (선택)
```

## 2. 기본 픽스처 (conftest.py)

프로젝트의 `conftest.py`에 이미 정의된 픽스처를 재사용한다:
- `user`: `User.objects.create_user(...)`
- `auth_client`: JWT 인증된 `APIClient`

앱별로 추가 픽스처가 필요하면 `{app}/tests/conftest.py`에 정의한다:

```python
import pytest
from {app}.models import {Model}

@pytest.fixture
def {model}(db):
    return {Model}.objects.create(
        {field1}="{value1}",
        {field2}="{value2}",
    )

@pytest.fixture
def {model}_list(db):
    return [{Model}.objects.create(...) for _ in range(3)]
```

## 3. ViewSet 테스트 패턴

```python
import pytest
from django.urls import reverse


@pytest.mark.django_db
class Test{Resource}ViewSet:

    # ── List ──────────────────────────────────────────
    def test_list_returns_200(self, auth_client):
        url = reverse("{resource}-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "results" in response.data  # 페이지네이션

    def test_list_unauthenticated_returns_401(self, client):
        url = reverse("{resource}-list")
        response = client.get(url)
        assert response.status_code == 401

    # ── Create ────────────────────────────────────────
    def test_create_valid_returns_201(self, auth_client):
        url = reverse("{resource}-list")
        payload = {
            "{field1}": "{valid_value}",
            "{field2}": "{valid_value}",
        }
        response = auth_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["{field1}"] == "{valid_value}"

    def test_create_invalid_{field}_returns_400(self, auth_client):
        url = reverse("{resource}-list")
        payload = {
            "{field1}": "{invalid_value}",  # 유효하지 않은 값
        }
        response = auth_client.post(url, payload, format="json")
        assert response.status_code == 400
        assert "{field1}" in response.data  # 에러 필드 확인

    # ── Retrieve ──────────────────────────────────────
    def test_retrieve_returns_200(self, auth_client, {model}):
        url = reverse("{resource}-detail", kwargs={"pk": {model}.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.data["id"] == {model}.pk

    def test_retrieve_not_found_returns_404(self, auth_client):
        url = reverse("{resource}-detail", kwargs={"pk": 99999})
        response = auth_client.get(url)
        assert response.status_code == 404

    # ── Partial Update ────────────────────────────────
    def test_partial_update_returns_200(self, auth_client, {model}):
        url = reverse("{resource}-detail", kwargs={"pk": {model}.pk})
        response = auth_client.patch(url, {"{field}": "{new_value}"}, format="json")
        assert response.status_code == 200
        {model}.refresh_from_db()
        assert {model}.{field} == "{new_value}"

    # ── Destroy ───────────────────────────────────────
    def test_destroy_returns_204(self, auth_client, {model}):
        url = reverse("{resource}-detail", kwargs={"pk": {model}.pk})
        response = auth_client.delete(url)
        assert response.status_code == 204

    # ── Custom Actions ────────────────────────────────
    def test_{custom_action}_returns_expected_shape(self, auth_client, {model}_list):
        url = reverse("{resource}-{custom-action-url-name}")
        response = auth_client.get(url)
        assert response.status_code == 200
        # 응답 shape 검증 (실제 데이터 구조 확인)
        assert "{expected_key}" in response.data
```

## 4. 비즈니스 규칙 테스트

Serializer의 `validate()` 로직과 서비스 규칙을 명시적으로 테스트한다:

```python
# 카테고리-소분류 매핑 검증 (BR-01 예시)
def test_create_with_invalid_subcategory_returns_400(self, auth_client):
    url = reverse("expense-list")
    payload = {
        "category": "FOOD",
        "sub_category": "TRANSPORT",  # FOOD의 하위분류가 아님
        ...
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 400
    assert "sub_category" in response.data
```

## 5. 필터링 & 정렬 테스트

```python
def test_filter_by_{field}(self, auth_client, {model}_list):
    url = reverse("{resource}-list")
    response = auth_client.get(url, {"{filter_param}": "{filter_value}"})
    assert response.status_code == 200
    # 필터 결과 검증
    for item in response.data["results"]:
        assert item["{field}"] == "{filter_value}"

def test_ordering_by_{field}_desc(self, auth_client, {model}_list):
    url = reverse("{resource}-list")
    response = auth_client.get(url, {"ordering": "-{field}"})
    assert response.status_code == 200
    values = [item["{field}"] for item in response.data["results"]]
    assert values == sorted(values, reverse=True)
```

## 6. 테스트 실행

```bash
# 특정 파일 실행
cd /Users/minsungkang/Desktop/study/crow-backend
poetry run pytest {app}/tests/test_{resource}_viewset.py -v

# 전체 실행
poetry run pytest -v

# 특정 클래스/메서드만
poetry run pytest {app}/tests/test_{resource}_viewset.py::Test{Resource}ViewSet::test_create_valid_returns_201 -v

# 실패한 테스트만 재실행
poetry run pytest --lf -v
```

## 7. 테스트 결과 보고서

`_workspace/03_qa_test_results.md`에 저장:
```markdown
# 테스트 결과

## 실행 요약
- 총 테스트: N개
- 통과: N개
- 실패: N개

## 통과한 테스트 목록
...

## 실패한 테스트 & 원인
### test_{name}
- 실패 메시지: `{error}`
- 원인 분석: {분석}
- 권장 수정: {방법}

## 커버리지 현황
- ViewSet 액션: {N}/{M} 커버
- 비즈니스 규칙: {N}/{M} 커버
- 미커버 영역: {목록}
```
