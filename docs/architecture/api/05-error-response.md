# 05. Error Response

API 에러는 HTTP status와 stable error code를 함께 사용합니다.

## Shape

```json
{
  "error": {
    "code": "RECIPE_NOT_FOUND",
    "message": "레시피를 찾을 수 없습니다.",
    "details": {}
  }
}
```

## Common Codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `VALIDATION_FAILED` | 요청 값이 유효하지 않음 |
| 401 | `UNAUTHENTICATED` | 인증 필요 |
| 403 | `FORBIDDEN` | 권한 없음 |
| 404 | `RESOURCE_NOT_FOUND` | 리소스 없음 |
| 409 | `CONFLICT` | 현재 상태와 요청이 충돌 |
| 422 | `UNPROCESSABLE_ENTITY` | 의미상 처리 불가 |
| 429 | `RATE_LIMITED` | 요청 한도 초과 |
| 500 | `INTERNAL_ERROR` | 서버 내부 오류 |
| 502 | `UPSTREAM_ERROR` | 외부 provider 오류 |
| 503 | `SERVICE_UNAVAILABLE` | 일시적 사용 불가 |

## Domain Codes

| Code | Usage |
| --- | --- |
| `RECIPE_NOT_FOUND` | 레시피 없음 |
| `RECIPE_SOURCE_NOT_FOUND` | 수집 원본 없음 |
| `RECIPE_SOURCE_NOT_IMPORTABLE` | import 가능한 lifecycle 상태가 아님 |
| `DUPLICATE_RECIPE_SOURCE` | 중복 수집 원본 |
| `PENDING_RECIPE_NOT_FOUND` | 사용자 제출 레시피 없음 |
| `PENDING_RECIPE_ALREADY_REVIEWED` | 이미 승인/거절된 사용자 제출 레시피 |
| `PENDING_RECIPE_ENRICH_FAILED` | 사용자 제출 레시피 AI 보정 실패 |
| `ALREADY_LIKED` | 이미 좋아요 누름 |
| `NOT_LIKED` | 좋아요 상태가 아님 |
| `ALREADY_SCRAPPED` | 이미 스크랩함 |
| `NOT_SCRAPPED` | 스크랩 상태가 아님 |
| `IMAGE_GENERATION_FAILED` | AI 이미지 생성 실패 |
| `IMAGE_GENERATION_NOT_FOUND` | 이미지 생성 후보 없음 |
| `IMAGE_GENERATION_NOT_SELECTABLE` | 선택할 수 없는 이미지 후보 |
| `EMBEDDING_FAILED` | embedding 생성 실패 |

## Validation Details

필드 단위 오류는 `details.fields`에 담습니다.

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "요청 값이 유효하지 않습니다.",
    "details": {
      "fields": [
        {
          "name": "difficulty",
          "reason": "easy, normal, hard 중 하나여야 합니다."
        }
      ]
    }
  }
}
```

## Conflict Details

상태 전이가 맞지 않는 경우 현재 상태와 필요한 상태를 내려줍니다.

```json
{
  "error": {
    "code": "RECIPE_SOURCE_NOT_IMPORTABLE",
    "message": "import 가능한 상태가 아닙니다.",
    "details": {
      "current": {
        "collection_status": "COLLECTED",
        "parse_status": "REVIEW_REQUIRED",
        "review_status": "PENDING",
        "import_status": "NOT_IMPORTED"
      },
      "required": {
        "collection_status": "COLLECTED",
        "parse_status": "PARSED",
        "review_status": "APPROVED",
        "import_status": "NOT_IMPORTED"
      }
    }
  }
}
```
