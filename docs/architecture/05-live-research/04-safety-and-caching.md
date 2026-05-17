# 04. Safety and Caching

Live Research는 외부 요청이 포함되므로 안전장치와 캐싱 정책이 필요하다.

## Safety

- 원문 레시피를 길게 복제하지 않는다.
- 출처 URL을 보존한다.
- 신뢰도가 낮은 정보는 단정하지 않는다.
- 영양/건강 관련 고위험 조언은 제한적으로 답한다.
- robots.txt와 이용약관을 확인한다.

## Rate Limit

초기 정책:

- 요청당 최대 검색 결과 5개
- 페이지 fetch 최대 3개
- 동일 query는 캐시 우선
- 실패 시 공격적 재시도 금지

## Cache Key

```text
live_research:{locale}:{normalized_query}:{date_bucket}
```

`date_bucket` 예:

- 트렌드성 질문: day
- 계절 메뉴: week
- 일반 정보: month

## Cache Payload

```json
{
  "query": "요즘 유행하는 레시피",
  "locale": "ko-KR",
  "evidence": [],
  "summary": "...",
  "created_at": "2026-05-13T12:00:00+09:00",
  "expires_at": "2026-05-14T12:00:00+09:00"
}
```

## Future Table

필요하면 캐시를 DB에 저장한다.

```text
live_research_cache
  cache_id
  cache_key
  query
  locale
  payload
  expires_at
  created_at
```
