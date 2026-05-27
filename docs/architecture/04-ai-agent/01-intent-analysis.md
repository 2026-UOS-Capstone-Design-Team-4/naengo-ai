# 01. Intent Analysis

사용자 입력이 들어오면 먼저 큰 작업군을 분류하고, 작업군별 planner가 세부
계획과 답변 전략을 만든다.

## Flow

```text
User Message
  -> MainIntentAgent
      RECIPE_FIND
      COOKING_QA
      PROFILE_MANAGEMENT
      SERVICE_QA
      SMALLTALK
      OFF_TOPIC
  -> DomainPlanner
      RecipeFindPlanner
      CookingQAPlanner
      ProfilePlanner/ProfilePolicy
  -> DomainAnswerRouter
```

## Main Intent Result

```json
{
  "primary_task": "RECIPE_FIND",
  "input_modes": ["TEXT", "IMAGE"],
  "confidence": 0.92,
  "needs_clarification": false,
  "clarification_question": null,
  "reason": "사용자가 보유 재료로 만들 수 있는 요리를 요청함"
}
```

기존 단일 라벨 호환 레이어는 제거하고, 내부 라우팅과 SSE metadata는
`primary_task`, `sub_intent`, `answer_strategy`를 기준으로 한다.

## Domain Planning

`RecipeFindPlanner`는 검색 쿼리, `sub_intent`, 재료, 알레르기, 식단 제약,
난이도, 검색 필요 여부, `answer_strategy`를 만든다.

`CookingQAPlanner`는 일반 요리 질문과 특정 레시피 참조 질문을 구분한다.
대화 상태와 사용자 프로필에서 온 알레르기, 식이 제한, 선호/비선호 재료,
요리 수준, 선호 조리 시간도 함께 참고해 대체 재료, 안전 민감 여부,
답변 난이도, 추가 검색 필요 여부, 최신 정보 필요 여부를 계획한다.
예를 들어 "첫 번째로 추천한 김치두부찌개에서 돼지고기 빼도 돼?"는 최근
추천 목록의 첫 번째 레시피를 참조하는 `sub_intent=RECIPE_CONTEXT`,
`answer_strategy=RECIPE_CONTEXT_QA`로 계획한다.

최종 answer agent는 `DomainAnswerRouter`가 선택한다. 예를 들어
`COOKING_QA + SAFETY`는 `safety_cooking_agent`,
`COOKING_QA + INGREDIENT_SUBSTITUTION`은 `ingredient_substitution_agent`,
`COOKING_QA + RECIPE_CONTEXT`는 `recipe_context_qa_agent`로 라우팅한다.

## Profile Update Flow

명시적인 프로필 관리 요청은 `PROFILE_MANAGEMENT`로 처리한다.

```text
MainIntentAgent(PROFILE_MANAGEMENT)
  -> ProfileUpdateAnalyzer / ProfileUpdatePolicy
      -> AUTO_SAVE
      -> REQUIRE_CONFIRMATION
      -> IGNORE
  -> UserProfileService (AUTO_SAVE인 경우)
```

추천 요청 안에 포함된 알레르기나 선호 정보는 추천 constraint로 우선 사용한다.
로그인 사용자의 `RECIPE_FIND` / `COOKING_QA` 턴에서는 동일한 문장을
profile side effect 후보로도 평가해, 명확한 장기 프로필 정보는 저장하고
애매한 정보는 확인 요청 이벤트로 보낸다.

AUTO_SAVE allowlist: `allergies`, `dietary_restrictions`,
`preferred_ingredients`, `disliked_ingredients`, `preferred_categories`,
`taste_keywords`, `cooking_skill`, `preferred_cooking_time_minutes`,
`serving_size`
