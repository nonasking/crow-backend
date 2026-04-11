---
name: drf-analyst
description: "DRF 백엔드 API 설계 및 요구사항 분석 스킬. 새로운 기능 요청을 받아 엔드포인트 구조, 모델 스키마, Serializer 스펙, 비즈니스 규칙을 정의한 명세서를 작성한다. crow-backend에 새 API를 추가하거나 기존 API를 수정/확장할 때, 또는 '어떤 엔드포인트가 필요한지', '어떤 모델을 만들어야 하는지' 분석이 필요할 때 반드시 이 스킬을 사용할 것."
---

# DRF API 분석 & 요구사항 정의 스킬

## 1. 코드베이스 파악 (항상 먼저)

명세를 작성하기 전에 기존 패턴을 파악한다:

1. 기존 앱 구조 확인 (`expenses/`, `authentication/` 등)
2. 유사한 모델/뷰셋 파일을 읽어 패턴을 추출한다
3. `constants.py`의 Enum 정의를 확인한다
4. `conftest.py`의 픽스처 구조를 파악한다

이를 통해 "이 프로젝트에서 어떻게 하는지"를 파악하고 일관성을 유지한다.

## 2. 엔드포인트 설계

각 리소스에 대해 다음을 정의한다:

```
### {Resource} API

| 메서드 | URL | 인증 | 설명 |
|--------|-----|------|------|
| GET    | /api/{resource}/ | JWT | 목록 조회 |
| POST   | /api/{resource}/ | JWT | 생성 |
| GET    | /api/{resource}/{id}/ | JWT | 단건 조회 |
| PATCH  | /api/{resource}/{id}/ | JWT | 부분 수정 |
| DELETE | /api/{resource}/{id}/ | JWT | 삭제 |
| GET    | /api/{resource}/{id}/{custom}/ | JWT | 커스텀 액션 |
```

**URL 설계 원칙:**
- 리소스는 복수형 명사 (`/expenses/`, `/budgets/`)
- 중첩 리소스는 2단계까지만 (`/expenses/{id}/tags/`)
- 동작은 URL이 아닌 HTTP 메서드로 표현
- 예외: 자연어로 명확한 경우 custom action 허용 (`/expenses/summary/`)

## 3. 모델 스키마 정의

```python
class {Model}(models.Model):
    # 각 필드: 이름, 타입, 옵션, verbose_name, 설명
    {field}: {FieldType}({옵션}, verbose_name="{한글명}")

    class Meta:
        db_table = "{table_name}"
        ordering = ["{default_ordering}"]
```

**필드 선택 가이드:**
- 분류/상태값 → `CharField(choices=Enum.choices)`
- 금액/수량 → `IntegerField` 또는 `DecimalField`
- 날짜 (시간 없음) → `DateField`
- 날짜+시간 → `DateTimeField`
- 선택적 텍스트 → `TextField(blank=True, default="")`
- 외래키 → `ForeignKey(on_delete=models.CASCADE)`

## 4. Serializer 스펙 정의

**model_serializers.py용 (CRUD 기본):**
```
ModelSerializer로 구현
fields: [전체 필드 목록]
validate(): 크로스 필드 규칙 명시
```

**api_serializers.py용 (커스텀 입출력):**
```
Serializer로 구현 (모델 직접 매핑 없음)
용도: 복잡한 쿼리 결과, 집계, 외부 데이터 변환
```

## 5. 비즈니스 규칙 정의

각 규칙을 다음 형식으로 명세한다:
```
규칙 BR-{N}: {규칙명}
- 조건: {언제}
- 동작: {무엇을}
- 오류 시: {HTTP 상태}, {에러 메시지}
- 구현 위치: serializer.validate() / service / model.save()
```

예시:
```
규칙 BR-01: 카테고리-소분류 매핑 검증
- 조건: Expense 생성/수정 시 sub_category가 category와 일치하지 않을 때
- 동작: ValidationError 발생
- 오류 시: 400, "'{sub_category}'은(는) '{category}'의 올바른 소분류가 아닙니다"
- 구현 위치: serializer.validate()
```

## 6. 요구사항 명세서 출력 형식

`_workspace/01_analyst_requirements.md`에 저장:

```markdown
# 요구사항 명세: {기능명}

## 기능 요약
{3-5줄 요약}

## 엔드포인트 설계
{위의 표 형식}

## 모델 스키마
{Python 코드 블록}

## Serializer 스펙
{model_serializers / api_serializers 구분}

## 비즈니스 규칙
{BR-N 형식 목록}

## 구현 가정사항
{불명확한 요구사항에 대한 합리적 가정}

## 구현 우선순위
1. {필수} ...
2. {권장} ...
3. {선택} ...
```
