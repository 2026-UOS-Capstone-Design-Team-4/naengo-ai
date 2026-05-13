# 00. Admin Review Overview

Admin Review는 `recipe_sources`에 수집된 외부 레시피 데이터를 사람이 확인하고 정식 `recipes`로 승격하는 운영 흐름입니다.

## Why

스크래핑 데이터는 바로 서비스에 노출하기 어렵습니다.

- 필수 필드가 비어 있을 수 있음
- 중복 데이터가 있을 수 있음
- 카테고리, 태그, 시간 같은 값의 정규화가 덜 되어 있음
- 이미지 S3 업로드가 실패할 수 있음
- 원문 문구나 이미지 권리 확인이 필요할 수 있음

따라서 수집과 파싱은 자동화하되, 서비스 노출 전 검수 상태를 분리합니다.

## Target Flow

```text
recipe_sources
  -> parse into recipe_source_extractions*
  -> admin list/detail
  -> edit extraction staging values
  -> approve / reject
  -> import to recipes*
```

## Status Flow

상태는 하나의 `status` 컬럼에 몰아넣지 않고 단계별로 분리합니다.

```text
collection_status
  COLLECTED | FAILED | SKIPPED

parse_status
  NOT_PARSED | PARSED | INVALID | DUPLICATE | REVIEW_REQUIRED

review_status
  PENDING | APPROVED | REJECTED

import_status
  NOT_IMPORTED | IMPORTED | FAILED
```

예시:

```text
COLLECTED + PARSED + PENDING + NOT_IMPORTED
  -> admin approves
COLLECTED + PARSED + APPROVED + NOT_IMPORTED
  -> import
COLLECTED + PARSED + APPROVED + IMPORTED
```

## Subdocuments

- [01. Recipe Source Review](01-recipe-source-review.md)
- [02. Review API](02-review-api.md)
- [03. Import Actions](03-import-actions.md)
- [04. Pending Recipe Enrichment](04-pending-recipe-enrichment.md)
