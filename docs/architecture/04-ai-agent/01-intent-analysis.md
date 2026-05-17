# 01. Intent Analysis

사용자 입력이 들어오면 먼저 의도를 분류하고, 그 결과로 처리 경로를 결정한다.

## Flow

```text
User Message
  -> RuleBasedFastPath       명백한 smalltalk/off-topic은 LLM 없이 처리
  -> LLMIntentClassifier     나머지는 LLM으로 분류
  -> IntentAgentRouter       intent에 따라 route 결정
```

## Intent Result

```json
{
  "is_cooking_related": true,
  "intent_type": "RECIPE_RECOMMENDATION",
  "confidence": 0.92,
  "reason": "사용자가 보유 재료로 만들 수 있는 요리를 요청함"
}
```

## Profile Update Flow

채팅에서 사용자 프로필에 반영할 수 있는 정보가 발견되면 `ProfileUpdateExtractor` → `ProfileUpdatePolicy`를 거친다.

```text
IntentClassifier(PROFILE_UPDATE)
  -> ProfileUpdateExtractor
  -> ProfileUpdatePolicy
      -> AUTO_SAVE              명확한 본인 정보, allowlist 필드
      -> REQUIRE_CONFIRMATION   모호한 주어, 기존 프로필과 충돌
      -> IGNORE                 타인 정보, 임시 조건, 농담
  -> UserProfileService (AUTO_SAVE인 경우)
```

AUTO_SAVE allowlist: `allergies`, `dietary_restrictions`, `preferred_ingredients`, `disliked_ingredients`, `preferred_categories`, `taste_keywords`, `cooking_skill`, `preferred_cooking_time_minutes`, `serving_size`
