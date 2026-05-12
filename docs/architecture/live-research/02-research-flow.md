# 02. Research Flow

## Flow

```text
1. AgentRouter가 live research 필요 여부를 판단한다.
2. LiveResearchService가 검색 query를 만든다.
3. SearchProvider가 후보 URL을 가져온다.
4. SourcePolicy가 후보를 필터링한다.
5. PageFetcher가 페이지를 가져온다.
6. ContentExtractor가 본문과 메타데이터를 추출한다.
7. EvidenceSummarizer가 핵심 정보를 요약한다.
8. CitationBuilder가 citation을 만든다.
9. AgentService가 evidence를 답변 context에 넣는다.
```

## Research Query

입력:

- intent result
- 사용자 메시지
- 사용자 위치/언어
- 계절/날짜
- 내부 DB 검색 결과 부족 여부

예:

```json
{
  "query": "2026 한국 SNS 인기 레시피",
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

- 검색 실패: DB 기반 답변으로 fallback
- 출처 품질 부족: “최신 자료를 충분히 확인하지 못했다”고 안내
- fetch 실패: 다음 후보 URL 시도
- 모든 후보 실패: live research 없이 일반 답변
