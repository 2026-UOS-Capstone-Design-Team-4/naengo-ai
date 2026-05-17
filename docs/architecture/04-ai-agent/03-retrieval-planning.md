# 03. Retrieval Planning

Retrieval Planning은 요리 관련 추천 요청을 검색에 적합한 구조로 바꾸는 단계다.

## Input

- 사용자 메시지
- 대화 이력
- 사용자 프로필
- 이미지 분석 결과
- intent result

## Output

```json
{
  "query_text": "김치와 두부로 만들 수 있는 쉬운 얼큰한 한식 요리",
  "target_dish_name": null,
  "available_ingredients": ["김치", "두부"],
  "main_ingredients": ["김치", "두부"],
  "avoid_ingredients": ["새우"],
  "required_ingredients": [],
  "cooking_time_max": 20,
  "difficulty": "easy",
  "cuisine_type": "한식",
  "dish_type": null,
  "cooking_method": null,
  "taste_keywords": ["얼큰함"],
  "diet_keywords": [],
  "servings": 2
}
```

## Search Strategy

1. planner가 query text와 filter 후보를 만든다.
2. `RecipeRetrievalService`가 embedding 검색을 수행한다.
3. score/cutoff 정책으로 낮은 품질 결과를 제외한다.
4. 필요한 경우 ingredient/category metadata로 rerank한다.
5. 사용자가 요리 이름을 직접 요청한 경우 `target_dish_name`을 title match rerank 신호로 사용한다.
6. 사용자가 재료 조합을 요청한 경우 `main_ingredients`를 강한 soft rerank 신호로 사용한다.

## Score Policy

초기 정책:

- score는 내부 판단용으로 사용한다.
- 프론트 응답에는 기본적으로 노출하지 않는다.
- cutoff 미만이면 `recipes` 이벤트를 비우고 일반 요리 제안과 구분한다.

## Future Reranking

- 사용자 선호 재료 가중치
- 싫어하는 재료 패널티
- 조리 시간 제한
- 난이도 제한
- 좋아요/스크랩 popularity boost
- 최근 추천 중복 회피
