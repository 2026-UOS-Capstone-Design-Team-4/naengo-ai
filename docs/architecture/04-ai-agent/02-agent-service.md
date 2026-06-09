# 02. Agent Service

`AgentService`는 채팅 API와 PydanticAI agent 사이의 application boundary다.

## Responsibilities

- 채팅 메시지 수신 및 이력 관리
- main intent classification 실행
- `AgentRunContext` 생성 및 요청 단위 상태 관리
- conversation state와 short-term / long-term memory 구성
- 현재 요청 조건과 사용자 프로필 조건 정리
- domain planner 실행
- 검색 근거와 답변 context 구성
- agent 실행 및 SSE 이벤트 생성
- answer verification 실행
- 검색된 레시피 결과 연결
- 채팅 메시지 저장

## Flow

```text
AgentService
  -> Common stream pipeline
      -> guest: no DB persistence
      -> logged-in: image upload, profile side effects, chat persistence
  -> MainIntentAgent
  -> ConversationStateResolver
      -> ConversationMemoryBuilder
      -> active constraints / recent recipe focus
  -> fixed response / clarification / profile management early routes
  -> DomainPlanner
      RECIPE_FIND
        -> ProfileUpdateAnalyzer/ProfileUpdatePolicy (로그인 side effect)
        -> RecipeFindPlanner
        -> retrieval plan
        -> sub_intent=BY_INGREDIENTS | TARGET_DISH | DIET_CONSTRAINT | ...
        -> answer_strategy=RECIPE_RECOMMENDATION

      COOKING_QA
        -> ProfileUpdateAnalyzer/ProfileUpdatePolicy (로그인 side effect)
        -> Apply conversation memory / profile context
        -> CookingQAPlanner
        -> AgentContextResolver (최근 추천 레시피 참조 해석)
        -> retrieval plan adapter (needs_retrieval=true인 경우)
        -> sub_intent=RECIPE_CONTEXT | INGREDIENT_SUBSTITUTION | SAFETY | ...
        -> answer_strategy=RECIPE_CONTEXT_QA | GENERAL_COOKING_QA | SAFETY_COOKING_QA

      PROFILE_MANAGEMENT
        -> ProfileUpdateAnalyzer/ProfileUpdatePolicy
        -> UserProfileService

      SMALLTALK / IDENTITY / OFF_TOPIC
        -> smalltalk_agent or fixed response

  -> LiveResearchService (domain plan 또는 정책상 최신 정보가 필요한 경우)
  -> DomainAnswerRouter
  -> RetrievalOrchestrator (retrieval이 필요한 경우)
        -> RecipeRetrievalService
        -> EvidencePack
  -> AgentQualityWorkflow (pydantic-graph, in-memory state)
      -> GenerateDraft
      -> VerifyAnswer
          -> Complete
          -> ReviseAnswer (최대 1회) -> VerifyAnswer
          -> SafetyFallback
  -> verified message / recipes
  -> StreamEventBuilder
```

## Agent Run Context

`AgentRunContext`는 한 요청 안에서 main intent, conversation state, domain plan,
live research, retrieval result, evidence, resolved context, answer strategy,
verification result를 묶는 실행 상태 객체다. 각 단계는 이 context를 갱신하고,
`AgentService`는 context를 기준으로 SSE와 저장을 조율한다.

답변 품질 루프는 별도 `AgentQualityWorkflow`가 담당한다. 그래프 상태는 요청
생명주기 동안 메모리에만 유지하며 DB checkpoint나 장애 후 resume는 제공하지
않는다. 생성 에이전트의 delta는 서버에서 모은 뒤 검증을 통과한 최종 답변만
단일 `message` 이벤트로 전송한다.

## Domain Answer Router

최종 answer agent는 `answer_strategy`만 보지 않고
`primary_task + domain_plan.sub_intent`를 함께 본다.

- `RECIPE_FIND` -> `recipe_agent`
- `COOKING_QA + RECIPE_CONTEXT` -> `recipe_context_qa_agent`
- `COOKING_QA + INGREDIENT_SUBSTITUTION` -> `ingredient_substitution_agent`
- `COOKING_QA + SAFETY` -> `safety_cooking_agent`
- 그 외 `COOKING_QA` -> `general_cooking_qa_agent`
- `SMALLTALK` -> `smalltalk_agent`

## Conversation State

`ConversationStateResolver`는 매 요청마다 대화 상태를 재구성한다.

- short-term memory: 최근 model message의 `recipe_ids`, 현재 prompt에서 추출한
  재료/임시 제외 조건
- long-term memory: `UserProfile` 기반 알레르기, 식이 제한, 선호/비선호 재료,
  요리 수준, 선호 조리 시간, 인분 수
- current focus: 최근 추천 중 사용자가 현재 가리키는 레시피
- active constraints: 현재 턴 또는 현재 대화 흐름에서 유지되는 조건
- rejected recipes: 사용자가 싫다고 한 최근 추천 결과

이 memory는 레시피 추천뿐 아니라 `COOKING_QA`의 세부 계획과 답변 생성에도
사용한다. 예를 들어 알레르기나 식이 제한은 대체 재료 후보와 안전 민감 답변에
반영하고, 요리 수준이나 선호 조리 시간은 답변 난이도와 안내 방식에 반영한다.

현재 구현은 별도 memory 테이블을 두지 않고, 채팅 메시지와 사용자 프로필에서
동적으로 구성한다.

## Evidence

검색 결과는 answer agent에 그대로 전달하기보다, 추천 이유와 주의 조건을 포함한
근거 context로 정리한다. 이 근거는 답변 생성과 검증 단계에서 함께 사용하며,
답변 텍스트와 `recipes` 이벤트가 서로 다른 내용을 말하지 않도록 돕는다.

## Context Resolver

`AgentContextResolver`는 `CookingQAPlanner`가 만든 레시피 참조를 실제 recipe id로
해석한다.

참조 소스:

- 요청에 명시된 recipe id
- 요청에 명시된 레시피 제목
- 최근 assistant message의 `recipe_ids`
- 현재 채팅방의 최근 추천 목록

예: 최근 추천이 `[12, 45, 77]`이고 사용자가
"두 번째로 추천한 된장찌개에서 두부를 빼도 돼?"라고 말하면
`resolved_recipe_id=45`로 해석한다.

## Answer Verification

`AnswerVerifier`는 추천 레시피와 답변이 사용자 제약과 충돌하지 않는지 검사한다.
알레르기, 제외 재료, 안전 민감 질문, payload 불일치가 핵심 검증 대상이다.
검증 실패는 로그에 남기고, 가능한 경우 문제가 있는 recipe payload를 제외하거나
revision agent가 기존 답변과 허용된 근거만 사용해 한 번 수정한다. 재검증 실패
시 recipe payload를 비우고 보수적인 고정 응답으로 정리한다.

## Tool Boundary

Agent tool은 DB session이나 embedding client를 직접 다루지 않는다.
레시피 검색은 `RecipeRetrievalService.search_recipes()`를 통해서만 수행한다.
`RecipeFindPlanner`가 `retrieval_required=false`로 판단한 턴에서는
answer agent의 tool 호출도 검색을 실행하지 않는다.
