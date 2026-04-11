---
name: drf-orchestrator
description: "crow-backend DRF 파이프라인 오케스트레이터. analyst → backend → qa → reviewer 에이전트 팀을 조율하여 새로운 Django REST Framework 기능을 엔드투엔드로 구현한다. 'DRF 기능 구현해줘', '새 API 추가', '엔드포인트 만들어줘', '모델/뷰셋/테스트 전체 작성', 'crow-backend에 추가' 요청 시 반드시 이 스킬을 사용할 것. 후속 작업: 구현 수정, 코드 재리뷰, 테스트 재실행, 특정 에이전트만 다시 실행, 이전 구현 개선, 업데이트, 보완 요청 시에도 이 스킬을 사용."
---

# DRF 파이프라인 오케스트레이터

crow-backend 프로젝트에 새로운 DRF 기능을 analyst → backend → qa → reviewer 파이프라인으로 구현하는 통합 스킬.

## 실행 모드: 에이전트 팀 (파이프라인)

## 에이전트 구성

| 팀원 | 에이전트 타입 | 역할 | 스킬 | 출력 |
|------|-------------|------|------|------|
| analyst | analyst (커스텀) | API 설계 & 요구사항 분석 | drf-analyst | `_workspace/01_analyst_requirements.md` |
| backend | backend (커스텀) | DRF 구현 | drf-backend | 구현 파일들 + `_workspace/02_backend_implementation_summary.md` |
| qa | qa (커스텀) | pytest 테스트 | drf-qa | 테스트 파일들 + `_workspace/03_qa_test_results.md` |
| reviewer | reviewer (커스텀) | 코드 리뷰 & 최적화 | drf-reviewer | `_workspace/04_reviewer_report.md` |

---

## 워크플로우

### Phase 0: 컨텍스트 확인

기존 산출물 존재 여부를 확인하여 실행 모드를 결정한다:

1. `/Users/minsungkang/Desktop/study/crow-backend/_workspace/` 디렉토리 존재 여부 확인
2. 실행 모드 결정:
   - **`_workspace/` 미존재** → 초기 실행. Phase 1로 진행
   - **`_workspace/` 존재 + 특정 에이전트만 재실행 요청** → 해당 에이전트부터 파이프라인 재시작
     (예: "테스트만 다시 실행" → qa부터, "리뷰만 다시" → reviewer부터)
   - **`_workspace/` 존재 + 새 기능 요청** → 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동 후 새 실행
3. 부분 재실행 시: 이전 `_workspace/` 파일들의 경로를 팀원 프롬프트에 포함

### Phase 1: 준비

1. 사용자 요청 분석 — 구현할 기능, 앱 위치, 우선순위 파악
2. `/Users/minsungkang/Desktop/study/crow-backend/_workspace/` 디렉토리 생성
3. 기존 코드베이스 컨텍스트 수집:
   - 관련 앱의 기존 모델/뷰셋 구조 확인
   - `pyproject.toml`에서 의존성 확인
4. 사용자에게 실행 계획 요약 보고 (팀 구성, 예상 산출물)

### Phase 2: 팀 구성

```
TeamCreate(
  team_name: "drf-pipeline",
  members: [
    {
      name: "analyst",
      agent_type: "analyst",
      model: "opus",
      prompt: """
        당신은 crow-backend DRF 프로젝트의 API 분석가입니다.
        drf-analyst 스킬을 활용하여 다음 기능을 분석하세요:

        [기능 요청]
        {사용자 요청 내용}

        [프로젝트 컨텍스트]
        - 위치: /Users/minsungkang/Desktop/study/crow-backend/
        - 기존 앱: expenses (Expense, Budget 모델), authentication
        - 패턴: ModelViewSet, model_serializers/api_serializers 분리, services 레이어

        작업:
        1. drf-analyst 스킬을 읽는다 (.claude/skills/drf-analyst/SKILL.md)
        2. 기존 관련 파일을 파악한다
        3. 요구사항 명세서를 _workspace/01_analyst_requirements.md에 작성한다
        4. 완료 시 SendMessage(to: "backend")로 파일 경로와 핵심 설계 결정을 전달한다
      """
    },
    {
      name: "backend",
      agent_type: "backend",
      model: "opus",
      prompt: """
        당신은 crow-backend DRF 프로젝트의 구현 담당자입니다.
        drf-backend 스킬을 활용하여 analyst의 명세를 구현하세요.

        [대기]
        analyst로부터 SendMessage를 받을 때까지 기다린 후 시작합니다.

        작업:
        1. drf-backend 스킬을 읽는다 (.claude/skills/drf-backend/SKILL.md)
        2. _workspace/01_analyst_requirements.md를 읽는다
        3. 기존 코드 파일을 읽고 프로젝트 패턴을 확인한다
        4. 모델, 시리얼라이저, 뷰셋, 서비스를 구현한다
        5. _workspace/02_backend_implementation_summary.md를 작성한다
        6. 완료 시 SendMessage(to: "qa")로 구현 파일 목록과 테스트 우선순위를 전달한다
        7. reviewer로부터 수정 요청이 오면 해당 파일만 수정하고 SendMessage(to: "qa")로 재테스트를 요청한다
      """
    },
    {
      name: "qa",
      agent_type: "qa",
      model: "opus",
      prompt: """
        당신은 crow-backend DRF 프로젝트의 QA 엔지니어입니다.
        drf-qa 스킬을 활용하여 테스트를 작성하고 실행하세요.

        [대기]
        backend로부터 SendMessage를 받을 때까지 기다린 후 시작합니다.

        작업:
        1. drf-qa 스킬을 읽는다 (.claude/skills/drf-qa/SKILL.md)
        2. _workspace/02_backend_implementation_summary.md와 구현 파일을 읽는다
        3. pytest-django 패턴으로 테스트를 작성한다
        4. `cd /Users/minsungkang/Desktop/study/crow-backend && poetry run pytest {테스트파일} -v`로 실행한다
        5. 실패한 테스트는 SendMessage(to: "backend")로 버그 보고를 보낸다
        6. 모든 테스트 통과 시 _workspace/03_qa_test_results.md를 작성하고 SendMessage(to: "reviewer")로 전달한다
        7. reviewer가 추가 테스트를 요청하면 해당 케이스를 추가하고 재실행한다
      """
    },
    {
      name: "reviewer",
      agent_type: "reviewer",
      model: "opus",
      prompt: """
        당신은 crow-backend DRF 프로젝트의 시니어 리뷰어입니다.
        drf-reviewer 스킬을 활용하여 구현 코드를 리뷰하세요.

        [대기]
        qa로부터 SendMessage를 받을 때까지 기다린 후 시작합니다.

        작업:
        1. drf-reviewer 스킬을 읽는다 (.claude/skills/drf-reviewer/SKILL.md)
        2. 모든 _workspace/ 파일과 구현 파일을 읽는다
        3. clean architecture, DRF 베스트 프랙티스, 보안, 성능을 검토한다
        4. Critical/Warning 이슈는 SendMessage(to: "backend")로 수정 요청을 보낸다
        5. _workspace/04_reviewer_report.md를 작성한다
        6. 최종 승인 시 리더(오케스트레이터)에게 완료를 알린다
      """
    }
  ]
)
```

**작업 등록:**
```
TaskCreate(tasks: [
  { title: "요구사항 분석 및 명세서 작성", assignee: "analyst" },
  { title: "DRF 구현 (모델/시리얼라이저/뷰셋/서비스)", assignee: "backend", depends_on: ["요구사항 분석 및 명세서 작성"] },
  { title: "pytest 테스트 작성 및 실행", assignee: "qa", depends_on: ["DRF 구현 (모델/시리얼라이저/뷰셋/서비스)"] },
  { title: "코드 리뷰 및 최종 보고서 작성", assignee: "reviewer", depends_on: ["pytest 테스트 작성 및 실행"] }
])
```

### Phase 3: 파이프라인 실행 (팀 자체 조율)

팀원들이 SendMessage와 TaskUpdate로 자체 조율하여 파이프라인을 진행한다.

**리더(오케스트레이터) 모니터링:**
- 팀원이 유휴 상태가 되면 자동 알림 수신
- 막힌 팀원에게 SendMessage로 힌트 또는 재지시
- TaskGet으로 전체 진행률 확인

**파이프라인 데이터 흐름:**
```
analyst → _workspace/01_analyst_requirements.md → backend
backend → 구현 파일들 + _workspace/02_backend_implementation_summary.md → qa
qa → 테스트 파일들 + _workspace/03_qa_test_results.md → reviewer
reviewer → _workspace/04_reviewer_report.md → 리더
```

**피드백 루프 처리:**
- reviewer → backend 수정 요청: backend가 수정 후 qa에게 재테스트 요청
- qa → backend 버그 보고: backend가 수정 후 qa에게 재테스트 요청
- 최대 2회 피드백 루프 후 해결되지 않으면 리더에게 에스컬레이션

### Phase 4: 결과 수집 및 정리

1. reviewer의 최종 완료 알림 수신
2. 팀원들에게 종료 알림 (SendMessage to: "all")
3. TeamDelete로 팀 정리
4. `_workspace/` 보존 (삭제하지 않음)
5. 사용자에게 결과 요약 보고:
   ```
   ## 구현 완료 요약
   
   ### 생성된 파일
   - ...
   
   ### 테스트 결과
   - 총 N개 / 통과 N개 / 실패 N개
   
   ### 리뷰 결과
   - Critical: N개 해결됨
   - Warning: N개 (N개 해결, N개 수용)
   
   ### 다음 단계
   - 마이그레이션: `poetry run python manage.py makemigrations {app} && poetry run python manage.py migrate`
   - API 문서: `poetry run python manage.py spectacular --file schema.yml`
   ```

---

## 데이터 흐름

```
[오케스트레이터]
    → TeamCreate(analyst, backend, qa, reviewer)
    → TaskCreate(4개 순차 태스크)
         │
         ▼
    [analyst] ──SendMessage──▶ [backend] ──SendMessage──▶ [qa] ──SendMessage──▶ [reviewer]
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼
  01_requirements.md    02_implementation.md    03_test_results.md    04_reviewer_report.md
                                 ↑                        │
                         SendMessage(버그)◀────────────────┘
                                 │
                         SendMessage(재테스트)──▶ [qa]
```

---

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| analyst 실패 | 재시작. 재실패 시 리더가 직접 기본 명세서 작성 후 backend 진행 |
| backend 구현 오류 (빌드 에러) | qa가 에러 내용을 backend에게 SendMessage. backend가 수정 |
| 테스트 계속 실패 (2회 이상) | qa가 리더에게 에스컬레이션. 리더가 개입하여 원인 분석 |
| reviewer 피드백 무한 루프 | 2회 피드백 후 "조건부 승인"으로 처리하고 이슈를 보고서에 기록 |
| 팀원 과반 실패 | 사용자에게 알리고 진행 여부 확인 |

---

## 테스트 시나리오

### 정상 흐름
1. 사용자: "Tag 모델 추가하고 Expense에 연결하는 API 만들어줘"
2. Phase 0: `_workspace/` 없음 → 초기 실행
3. Phase 1: expenses 앱 파악, `_workspace/` 생성
4. Phase 2: 4명 팀 구성, 4개 순차 태스크 등록
5. analyst: Tag 모델 스키마 + `/expenses/{id}/tags/` 엔드포인트 설계 → backend에 전달
6. backend: Tag 모델, TagSerializer, ExpenseTagViewSet 구현 → qa에 전달
7. qa: test_expense_tag_viewset.py 작성, pytest 실행 → reviewer에 전달
8. reviewer: CRUD 확인, `@extend_schema` 누락 Warning 발견 → backend에 수정 요청
9. backend: 수정 완료 → qa 재테스트 → reviewer 최종 승인
10. 결과: `_workspace/04_reviewer_report.md` + 구현 파일들 완성

### 에러 흐름
1. backend 구현 후 qa가 pytest 실행 → `ImportError: cannot import name 'Tag'` 발생
2. qa가 backend에게 SendMessage: "Tag 모델 import 경로 오류 - models/__init__.py에 re-export 누락"
3. backend: `expenses/models/__init__.py`에 `from .tag import Tag` 추가
4. qa: 재실행 → 전체 통과 → reviewer에 전달

---

## 부분 재실행 예시

```
사용자: "테스트만 다시 실행해줘"
→ Phase 0: _workspace/ 존재 확인
→ qa 에이전트만 생성 (단일 서브 에이전트로)
→ _workspace/02_backend_implementation_summary.md 읽고 테스트 재실행
→ 결과를 _workspace/03_qa_test_results.md에 덮어쓰기

사용자: "reviewer 리뷰만 다시 해줘"
→ Phase 0: _workspace/ 존재 확인
→ reviewer 에이전트만 생성
→ 기존 _workspace/ 파일들을 모두 읽고 리뷰 수행
```
