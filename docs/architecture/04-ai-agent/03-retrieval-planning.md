# 03. Retrieval Planning

Retrieval Planning은 `RECIPE_FIND` 요청을 검색에 적합한 구조로 바꾸는 단계다.

## Input

- 사용자 메시지
- 대화 이력
- 사용자 프로필
- 이미지 분석 결과
- main intent result
- 사용자 프로필 context
- conversation state context
- short-term / long-term memory context
- 현재 요청의 임시 조건과 안전 조건

## Output

retrieval planning의 출력은 검색을 실행하기 위한 구조화된 계획이다. 계획에는
검색 문장, 세부 의도, 보유 재료, 제외 재료, 알레르기, 시간/난이도 조건,
요리명 힌트, 답변 전략이 포함된다. 이 값들은 검색, rerank, 답변 생성, 검증
단계가 같은 조건을 바라보도록 하는 공통 계약이다.

## Search Strategy

1. planner가 검색 의도와 조건을 정리한다.
2. `retrieval_required=true`이면 retrieval 계층이 embedding, title, ingredient 기반 후보를 모은다.
3. 알레르기, 제외 재료, 시간 제한 같은 hard constraint를 우선 반영한다.
4. 보유 재료, 요리명, 취향, 난이도, 최근 추천 중복 여부를 기준으로 rerank한다.
5. 최종 후보를 answer agent가 이해할 수 있는 evidence context로 요약한다.

전체 검색 계획으로 후보가 부족할 때는 soft 조건만 완화할 수 있다. 이 경우에도
알레르기, 제외 재료, 필수 재료, 조리 시간 같은 hard constraint는 유지한다.

planner가 `clarification_required=true` 또는 `sub_intent=CLARIFICATION`을 반환하면
검색 전에 확인 질문으로 응답하고 RAG prefetch를 수행하지 않는다.

`COOKING_QA`에서도 planner가 `needs_retrieval=true`를 반환하면 같은
retrieval 흐름을 사용한다. 이때 요리 QA 계획은 검색 계층이 이해할 수 있는
retrieval plan으로 변환되어 target dish, 참조 재료, 사용자 제약을 같은 계약으로
전달한다.

## Score Policy

초기 정책:

- score는 내부 판단용으로 사용한다.
- 프론트 응답에는 기본적으로 노출하지 않는다.
- cutoff 미만이면 `recipes` 이벤트를 비우고 일반 요리 제안과 구분한다.

## Future Reranking

- 좋아요/스크랩 popularity boost
- 최근 추천 중복 회피
- 사용자 피드백 기반 선호도 보정
