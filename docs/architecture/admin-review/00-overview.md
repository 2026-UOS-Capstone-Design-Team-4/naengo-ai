# 00. Admin Review Overview

Admin Review는 `recipe_sources`에 수집된 외부 레시피 데이터를 사람이 확인하고 정식 `recipes`로 승격하는 운영 흐름이다.

## Why

스크래핑 데이터는 바로 서비스에 노출하기 어렵다.

- 필수 필드가 빠질 수 있음
- 중복일 수 있음
- 카테고리/난이도 정규화가 틀릴 수 있음
- 이미지 S3 업로드가 실패할 수 있음
- 원문 문구나 이미지 권리 확인이 필요할 수 있음

따라서 `READY` 데이터는 자동 import할 수 있지만, `REVIEW_REQUIRED`, `INVALID`, `DUPLICATE`는 관리자 검수 흐름이 필요하다.

## Target Flow

```text
recipe_sources
  -> admin list/detail
  -> edit normalized payload
  -> approve / reject / mark duplicate / retry
  -> import to recipes
```

## Status Flow

```text
COLLECTED
  -> PARSED
  -> READY
      -> IMPORTED
  -> REVIEW_REQUIRED
      -> READY
      -> REJECTED
  -> INVALID
      -> REVIEW_REQUIRED
      -> REJECTED
  -> DUPLICATE
      -> REJECTED
      -> READY
```

## Subdocuments

- [01. Recipe Source Review](01-recipe-source-review.md)
- [02. Review API](02-review-api.md)
- [03. Import Actions](03-import-actions.md)
- [04. Pending Recipe Enrichment](04-pending-recipe-enrichment.md)
