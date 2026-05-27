# 03. Agent Integration

Live Research는 main intent와 domain plan이 최신성 필요성을 감지했을 때
보조 context로 연결된다.

## Primary Tasks

Live Research 정보가 필요할 수 있는 task:

- `RECIPE_FIND`
- `COOKING_QA`

추가 flag:

```json
{
  "needs_live_research": true,
  "requires_freshness": true,
  "requires_external_evidence": true
}
```

## Routing

```text
MainIntentAgent
  -> DomainPlanner
      -> if fresh/current/trend/external evidence required:
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
  "primary_task": "RECIPE_FIND",
  "used_live_research": true,
  "source_count": 3
}
```
