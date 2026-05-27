# 02. Research Flow

## Flow

```text
1. Main intent 이후 domain plan과 research 정책이 live research 필요 여부를 판단한다.
2. LiveResearchService가 검색 query를 만든다.
3. SearchProvider가 정보 URL을 가져온다.
4. SourcePolicy가 정보를 필터링한다.
5. 검색 결과의 제목, 출처, 날짜, 요약 정보를 evidence로 정리한다.
6. CitationBuilder가 answer context를 만든다.
7. AgentService가 evidence를 포함한 context에 넣는다.
```

페이지 본문 fetch, content extraction, 별도 summarization은 더 풍부한 외부 근거가
필요할 때 확장할 수 있는 단계다. 기본 흐름은 검색 provider가 제공한 후보
metadata와 snippet을 짧은 evidence로 정리하는 데 초점을 둔다.

## Research Query

입력:

- main intent result
- domain plan
- 사용자 메시지
- 사용자 위치/언어
- 계절/날짜
- 기존 DB 검색 결과 부족 신호

출력:

```json
{
  "query": "2026 한국 SNS 인기 음식",
  "locale": "ko-KR",
  "freshness_required": true,
  "topic": "food_trend",
  "max_sources": 5
}
```

## Result Shape

```json
{
  "answer_context": "요즘 SNS에서는 ...",
  "evidence": [
    {
      "title": "문서 제목",
      "url": "https://...",
      "summary": "핵심 내용",
      "published_at": "2026-05-01"
    }
  ],
  "used_at": "2026-05-13T12:00:00+09:00"
}
```

## Failure Behavior

- 검색 실패: DB 기반 응답으로 fallback
- 출처 품질 부족: "최우선 자료로 충분히 확인하지 못했다"고 안내
- 후보 수집/요약 실패: 다음 정보 URL 또는 일반 응답 시도
- 모든 정보 실패: live research 없이 일반 응답
