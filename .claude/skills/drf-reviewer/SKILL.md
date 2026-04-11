---
name: drf-reviewer
description: "DRF 코드 리뷰 및 리팩토링 스킬. 구현된 코드의 clean architecture 준수, DRF 베스트 프랙티스, 보안, 성능, 유지보수성을 평가하고 개선 방향을 제시한다. '코드 리뷰', '리팩토링', '코드 품질 확인', '개선점 찾아줘', '베스트 프랙티스 확인' 요청 시 반드시 이 스킬을 사용할 것."
---

# DRF 코드 리뷰 & 리팩토링 스킬

## 1. 리뷰 순서

모든 관련 파일을 읽기 전에 리뷰를 시작하지 않는다:

1. `_workspace/01_analyst_requirements.md` — 원래 의도 파악
2. `_workspace/02_backend_implementation_summary.md` — 구현 범위
3. `_workspace/03_qa_test_results.md` — 테스트 결과
4. 실제 구현 파일들 — 상세 리뷰

## 2. Clean Architecture 검사 기준

**뷰(ViewSet)에 있어서는 안 되는 것:**
```python
# BAD: 비즈니스 로직이 view에 있음
def create(self, request, *args, **kwargs):
    if request.data["amount"] > 1000000:
        # 복잡한 비즈니스 로직...
        Notification.objects.create(...)
    return super().create(request, *args, **kwargs)

# GOOD: 서비스 레이어에 위임
def create(self, request, *args, **kwargs):
    return super().create(request, *args, **kwargs)
# 로직은 serializer.save() → service에서 처리
```

**서비스 레이어에 있어야 하는 것:**
- 복잡한 쿼리 로직
- 여러 모델에 걸친 트랜잭션
- 외부 API 호출
- 이메일/알림 발송

**모델에 있어서는 안 되는 것:**
- HTTP 관련 코드
- 직접적인 비즈니스 워크플로우
- 다른 앱 모델에 대한 복잡한 의존

## 3. DRF 베스트 프랙티스 체크리스트

### Serializer
```python
# GOOD: PATCH 시 self.instance fallback
def validate(self, attrs):
    instance = self.instance
    category = attrs.get("category", instance.category if instance else None)
    ...

# BAD: PATCH에서 None이 될 수 있음
def validate(self, attrs):
    category = attrs["category"]  # PATCH 시 KeyError 가능
```

```python
# GOOD: 에러 필드를 딕셔너리로 특정
raise serializers.ValidationError({"sub_category": "..."})

# BAD: 필드를 특정하지 않음
raise serializers.ValidationError("잘못된 소분류입니다")
```

### ViewSet
```python
# GOOD: 모든 액션에 @extend_schema
@extend_schema(summary="Expense 생성")
def create(self, request, *args, **kwargs):
    return super().create(request, *args, **kwargs)

# BAD: 문서화 없음
def create(self, request, *args, **kwargs):
    return super().create(request, *args, **kwargs)
```

```python
# GOOD: custom action에 serializer_class 명시
@action(detail=False, methods=["get"], serializer_class=SummarySerializer)
def summary(self, request):
    ...

# BAD: get_serializer()가 기본 serializer를 사용
@action(detail=False, methods=["get"])
def summary(self, request):
    serializer = self.get_serializer(...)  # 기본 serializer 사용
```

### 쿼리 최적화
```python
# N+1 의심 패턴 탐지
queryset = Model.objects.all()
# ForeignKey 관계가 있다면 select_related 확인
queryset = Model.objects.select_related("related_model")
queryset = Model.objects.prefetch_related("related_set")
```

## 4. 이슈 분류 기준

**Critical — 반드시 수정:**
- 기능 오류 (비즈니스 규칙 미구현)
- 보안 취약점 (인증 누락, SQL injection 가능성)
- 데이터 정합성 문제 (잘못된 validate 로직)
- 테스트가 실패하는 버그

**Warning — 강하게 권장:**
- Clean Architecture 위반 (비즈니스 로직이 view에 있음)
- `@extend_schema` 누락
- PATCH validate에 `self.instance` fallback 없음
- 중복 코드 (동일한 validate 로직이 여러 serializer에)
- N+1 쿼리

**Suggestion — 선택적 개선:**
- 타입 힌트 추가
- 독스트링 개선
- 상수 추출 (하드코딩된 문자열)
- 더 명확한 변수명

## 5. 리뷰 보고서 형식

`_workspace/04_reviewer_report.md`에 저장:

```markdown
# 코드 리뷰 보고서

## 총평
{전반적인 코드 품질 평가 2-3문장}

## Critical 이슈 ({N}개)
### [CRITICAL-01] {이슈명}
- **파일:** `{파일경로}:{라인번호}`
- **문제:** {구체적 문제 설명}
- **수정 방법:**
  ```python
  # Before
  {현재 코드}
  
  # After
  {수정 코드}
  ```

## Warning ({N}개)
### [WARN-01] {이슈명}
- **파일:** `{파일경로}`
- **문제:** {문제}
- **권장 수정:** {방법}

## Suggestion ({N}개)
- [SUGG-01] `{파일}`: {제안}
- [SUGG-02] `{파일}`: {제안}

## 최종 승인
- [ ] Critical 이슈 모두 해결됨
- [ ] Warning 이슈 해결 또는 수용됨
- **승인 여부:** {승인 / 조건부 승인 / 반려}
```

## 6. 리팩토링 패턴

### 중복 validate 로직 추출
```python
# BEFORE: 중복
class ExpenseSerializer(ModelSerializer):
    def validate(self, attrs):
        # 동일한 카테고리 검사 로직...

class BudgetSerializer(ModelSerializer):
    def validate(self, attrs):
        # 동일한 카테고리 검사 로직...

# AFTER: 공통 믹스인
class CategoryValidationMixin:
    def validate_category_subcategory(self, attrs, instance=None):
        category = attrs.get("category", getattr(instance, "category", None))
        sub_category = attrs.get("sub_category", getattr(instance, "sub_category", None))
        if category and sub_category:
            allowed = CATEGORY_SUBCATEGORY_MAP.get(category, [])
            if sub_category not in allowed:
                raise serializers.ValidationError({"sub_category": f"..."})
        return attrs
```
