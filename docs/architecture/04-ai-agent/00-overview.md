# 00. AI Agent Overview

AI Agent는 사용자의 채팅 입력을 해석하고, 필요한 경우 레시피 검색이나
live research를 수행해 SSE 스트림으로 답변과 추천 결과를 반환한다.

## Flow

```text
ChatService
  -> AgentService
      -> MainIntentAgent          큰 작업군 분류
      -> AgentRunContext          요청 단위 실행 상태
      -> ConversationMemory       short-term / long-term memory 구성
      -> DomainPlanner            작업별 세부 계획 생성
      -> AgentContextResolver     최근 추천/레시피 참조 해석
      -> LiveResearchService      최신/외부 근거가 필요한 경우 보조 context 구성
      -> RetrievalOrchestrator    RAG 검색, profile-aware rerank, 결과 정규화
      -> DomainAnswerRouter       main intent/sub intent 기반 agent 선택
      -> AnswerVerifier           알레르기/추천 모순 검증
      -> StreamEventBuilder       SSE 이벤트 생성
```

## Primary Tasks

| Task | 설명 |
| --- | --- |
| `RECIPE_FIND` | 레시피 추천, 검색, 필터링, 보유 재료 기반 제안 |
| `COOKING_QA` | 조리법, 대체 재료, 보관, 안전, 영양 관련 질문 |
| `PROFILE_MANAGEMENT` | 사용자 프로필 저장, 수정, 삭제, 조회 요청 |
| `IDENTITY` | 챗봇의 정체성, 역할, 기능 범위 질문 |
| `SMALLTALK` | 가벼운 일상 대화 |
| `OFF_TOPIC` | 요리와 무관한 질문 |

식단/알레르기, 이미지 입력, 대체 재료 같은 세부 성격은 top-level task가
아니라 constraint, input mode, sub_intent, answer_strategy로 처리한다.

## Answer Strategies

| Strategy | 설명 |
| --- | --- |
| `RECIPE_RECOMMENDATION` | 레시피 검색 결과를 기반으로 짧은 추천 답변 생성 |
| `RECIPE_CONTEXT_QA` | 최근 추천 또는 명시된 레시피를 참조해 답변 |
| `GENERAL_COOKING_QA` | 일반 조리 지식 답변 |
| `SAFETY_COOKING_QA` | 보관, 식중독, 덜 익음 등 안전 민감 답변 |
| `PROFILE_ACTION` | 프로필 저장/수정/삭제/확인 응답 |
| `CLARIFICATION` | 추가 정보 요청 |
| `FIXED` | 고정 응답 |
| `SMALLTALK` | 잡담 응답 |

## Domain Sub Intents

각 main intent의 planner는 도메인 안에서 더 작은 `sub_intent`를 만든다.
최종 answer agent는 `primary_task + sub_intent + context_state`를 기준으로 선택한다.

초기 분리 대상:

- `RECIPE_FIND`: `BY_INGREDIENTS`, `TARGET_DISH`, `DIET_CONSTRAINT`,
  `IMAGE_INGREDIENTS`, `QUICK_MEAL`, `CLARIFICATION`
- `COOKING_QA`: `RECIPE_CONTEXT`, `INGREDIENT_SUBSTITUTION`, `TECHNIQUE`,
  `STORAGE`, `SAFETY`, `NUTRITION`, `GENERAL`

`answer_strategy`는 agent 선택의 단독 기준이 아니라 답변 방식과 정책 힌트로 사용한다.

## Profile Update Policy

채팅 중 사용자 취향, 알레르기, 식이 제한 같은 정보가 발견되면 바로 DB에
쓰지 않고 정책에 따라 분류한다.

- `AUTO_SAVE`: 명확한 1인칭 본인 정보이고 allowlist 필드에 해당하면 자동 저장
- `REQUIRE_CONFIRMATION`: 주어가 모호하거나 기존 프로필과 충돌하면 사용자 확인 요청
- `IGNORE`: 타인 정보, 임시 조건, 농담 등은 저장하지 않음

## Memory Layers

Agent memory는 두 층으로 분리한다.

- short-term memory: 현재 채팅방의 최근 추천 recipe ids, 최근 재료, 현재 턴의 임시 제약
- long-term memory: `UserProfile`에 저장된 알레르기, 싫어하는/좋아하는 재료,
  식이 제한, 요리 수준, 선호 조리 시간, 인분 수

short-term memory는 "첫 번째로 추천한 김치두부찌개"처럼 이전 추천을
가리키는 참조 해석과 현재 대화 제약에 쓰고,
long-term memory는 검색 hard filter/rerank, domain planning, 답변 개인화,
검증에 함께 사용한다.

## Live Research

DB 검색만으로 답하기 어려운 최신 트렌드, 최근 이슈, 외부 근거가 필요한
경우에만 선택적으로 사용한다. 기본 레시피 추천은 DB RAG 검색을 우선한다.

## Quality Evolution

챗봇 품질 개선은 agent 수를 늘리는 방식보다 대화 흐름의 각 단계를 명확히
나누는 방향으로 진행한다.

```text
User Message
  -> Input Understanding
  -> Conversation State
  -> Intent and Domain Planning
  -> Constraint Handling
  -> Retrieval and Evidence
  -> Answer Generation
  -> Verification
  -> Streaming Response
```

핵심 원칙:

- 대화 상태는 최근 추천, 현재 참조 대상, 임시 조건, 사용자 프로필을 함께 본다.
- 알레르기, 제외 재료, 조리 시간 같은 조건은 검색, 요리 QA 계획, 답변 검증에서
  함께 사용한다.
- 검색 결과는 답변에 쓸 수 있는 근거로 요약해 answer agent에 전달한다.
- 답변 전 검증 단계에서 추천 payload와 텍스트가 서로 어긋나지 않는지 확인한다.
- 대표 대화 케이스로 intent, retrieval, safety, consistency를 지속적으로 평가한다.

## Subdocuments

- [01. Intent Analysis](01-intent-analysis.md)
- [02. Agent Service](02-agent-service.md)
- [03. Retrieval Planning](03-retrieval-planning.md)
- [04. Streaming Events](04-streaming-events.md)
- [05. Testing Strategy](05-testing-strategy.md)
- [Live Research](../05-live-research/00-overview.md)
