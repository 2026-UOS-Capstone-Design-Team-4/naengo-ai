# 03. Agent Integration

Live Research는 AI Agent의 route 중 하나로 연결된다.

## Intent Types

Live Research 정보가 필요한 intent:

- `RECIPE_RECOMMENDATION`
- `COOKING_TIP`
- `INGREDIENT_SUBSTITUTION`
- `DIET_OR_ALLERGY`

추가 flag:

```json
{
  "requires_freshness": true,
  "requires_external_evidence": true
}
```

## Routing

```text
IntentClassifier
  -> IntentAgentRouter
      -> if fresh/current/trend required:
           LiveResearchService
      -> else:
           RecipeRetrievalService
```

## Combined Answer

기존 DB와 live research를 함께 쓸 수 있다.

```text
1. 기존 DB에서 관련 정보 검색
2. live research로 최신 트렌드 맥락 확인
3. AI 응답은 DB 정보를 우선 추천
4. 최신 정보는 보조 설명과 출처를 제공
```

## Prompt Context

Agent에 전달하는 live research context는 짧고 구조화한다.

```text
Live research evidence:
- Source: ...
- Published: ...
- Summary: ...
```

원문 전체를 prompt에 넣지 않는다.

## SSE Metadata

`metadata` 이벤트에 research 활용 여부를 표시할 수 있다.

```json
{
  "intent_type": "RECIPE_RECOMMENDATION",
  "used_live_research": true,
  "source_count": 3
}
```
