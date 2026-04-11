---
name: drf-backend
description: "DRF 모델, 시리얼라이저, 뷰셋, 서비스 구현 스킬. crow-backend 프로젝트 패턴(ModelViewSet, services 레이어, model_serializers/api_serializers 분리)에 맞게 실제 코드를 작성한다. '구현해줘', '코드 작성', '모델 만들어줘', '뷰셋 추가', '서비스 로직 작성' 요청 시 반드시 이 스킬을 사용할 것."
---

# DRF 구현 스킬

## 1. 구현 전 필수 확인

구현 전에 관련 기존 파일을 반드시 읽는다:
- 유사한 앱의 모델, 시리얼라이저, 뷰셋 파일
- `constants.py` (기존 Enum 재사용)
- `urls.py` (라우터 등록 패턴)
- `conftest.py` (테스트 픽스처 — 구현 완료 후 qa 참조용)

## 2. 모델 구현 패턴

```python
# {app}/models/{model}.py
from django.db import models
from {app}.constants import {EnumClass}

class {Model}(models.Model):
    {field} = models.{FieldType}(
        {옵션},
        verbose_name="{한글명}",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "{table_name}"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.{main_field}}"
```

```python
# {app}/models/__init__.py — 모델 re-export 필수
from .{model} import {Model}
```

**마이그레이션:** 코드만 작성하고 아래 명령 지침을 제공한다:
```bash
poetry run python manage.py makemigrations {app}
poetry run python manage.py migrate
```

## 3. Serializer 구현 패턴

### model_serializers.py (CRUD용)
```python
from rest_framework import serializers
from {app}.models import {Model}

class {Model}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {Model}
        fields = [
            "id",
            "{field1}",
            "{field2}",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        # PATCH 시 부분 업데이트 고려 — 기존 값 fallback
        instance = self.instance
        {field} = attrs.get("{field}", instance.{field} if instance else None)

        # 크로스 필드 검사 로직
        if {condition}:
            raise serializers.ValidationError({
                "{field}": "{에러 메시지}"
            })

        return attrs
```

### api_serializers.py (커스텀 입출력용)
```python
class {Custom}Serializer(serializers.Serializer):
    {field} = serializers.{FieldType}()

    def {custom_method}(self):
        # 서비스 레이어 호출
        from {app}.services import {service_function}
        return {service_function}(self.validated_data)
```

**중복 validate 로직이 있으면** `mixins.py`나 공통 함수로 추출한다.

## 4. ViewSet 구현 패턴

```python
# {app}/views/{resource}_viewset.py
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from {app}.filters import {Resource}Filter
from {app}.models import {Model}
from {app}.pagination import {App}Pagination
from {app}.serializers.model_serializers import {Model}Serializer
from {app}.serializers.api_serializers import {Custom}Serializer


class {Resource}ViewSet(ModelViewSet):
    queryset = {Model}.objects.all()
    serializer_class = {Model}Serializer
    pagination_class = {App}Pagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = {Resource}Filter
    ordering_fields = ["{field1}", "{field2}"]
    ordering = ["-created_at"]

    @extend_schema(summary="{Resource} 생성")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="{Resource} 목록 조회")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="{Resource} 단건 조회")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="{Resource} 수정")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="{Resource} 부분 수정")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="{Resource} 삭제")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(summary="{custom action 설명}")
    @action(detail=False, methods=["get"], url_path="{url-path}")
    def {custom_action}(self, request):
        # 서비스 레이어 호출
        from {app}.services import {service_function}
        result = {service_function}(request.query_params)
        return Response(result)
```

## 5. Service 레이어 패턴

비즈니스 로직은 views에 넣지 않고 `services/` 또는 `services.py`에 분리한다:

```python
# {app}/services/{domain}.py
from {app}.models import {Model}

def {action}_{resource}(data: dict) -> dict:
    """
    {기능 설명}
    Args:
        data: {입력 설명}
    Returns:
        {출력 설명}
    Raises:
        RuntimeError: {에러 조건}
    """
    # 비즈니스 로직 구현
    ...
```

서비스 함수는 순수 Python으로 작성 — HTTP 관심사(Request/Response) 없음.

## 6. URL 등록 패턴

```python
# {app}/urls.py
from rest_framework.routers import DefaultRouter
from {app}.views.{resource}_viewset import {Resource}ViewSet

router = DefaultRouter()
router.register(r"{resource}", {Resource}ViewSet, basename="{resource}")

urlpatterns = router.urls
```

## 7. 구현 요약 작성

`_workspace/02_backend_implementation_summary.md`에 저장:
```markdown
# 구현 요약

## 생성/수정된 파일
- `{app}/models/{model}.py` — {설명}
- `{app}/serializers/model_serializers.py` — {변경사항}
- `{app}/views/{resource}_viewset.py` — {설명}
- `{app}/services/{domain}.py` — {설명}

## 주요 설계 결정
- {결정사항과 이유}

## 테스트 우선순위
1. {가장 중요한 로직}
2. {경계 케이스}

## 마이그레이션 명령
```bash
poetry run python manage.py makemigrations {app}
poetry run python manage.py migrate
```
```
