# 02. Review API

Admin Review API는 `recipe_sources` 검수와 import action을 제공합니다. AI 이미지 재생성도 관리자 액션으로 둡니다.

## Recipe Source Endpoints

```text
GET    /api/v1/admin/recipe-sources
GET    /api/v1/admin/recipe-sources/{source_id}
PATCH  /api/v1/admin/recipe-sources/{source_id}
POST   /api/v1/admin/recipe-sources/{source_id}/approve
POST   /api/v1/admin/recipe-sources/{source_id}/reject
POST   /api/v1/admin/recipe-sources/{source_id}/retry-normalize
POST   /api/v1/admin/recipe-sources/{source_id}/retry-images
POST   /api/v1/admin/recipe-sources/{source_id}/import
```

## Image Generation Endpoints

```text
GET    /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

일반 사용자용 레시피 조회 API에는 이미지 생성 액션을 넣지 않습니다. 생성은 비용과 검수 책임이 있으므로 관리자 API에서만 수행합니다.

## List Query

```text
GET /api/v1/admin/recipe-sources?status=REVIEW_REQUIRED&source_site=10000recipe&limit=50&cursor=...
```

Query params:

- `status`
- `source_site`
- `parser_type`
- `has_errors`
- `cursor`
- `limit`

## Patch Source

`PATCH`는 import 전 normalized data를 수정합니다.

```json
{
  "normalized_payload": {
    "recipe": {
      "title": "수정한 제목",
      "difficulty": "easy"
    }
  },
  "normalized_metadata": {
    "main_ingredients": ["김치", "돼지고기"]
  },
  "status": "READY"
}
```

## Approve

```text
POST /api/v1/admin/recipe-sources/{source_id}/approve
```

동작:

- validation을 다시 수행합니다.
- 문제가 없으면 `status = READY`로 변경합니다.
- 자동 import는 하지 않습니다.

## Import

```text
POST /api/v1/admin/recipe-sources/{source_id}/import
```

동작:

- `READY` 상태만 import 가능합니다.
- `recipes`, `recipe_ingredients`, `recipe_steps`를 생성합니다.
- embedding을 생성합니다.
- 대표 이미지가 없으면 AI 이미지 생성 후보를 요청할 수 있습니다.
- `recipe_sources.status = IMPORTED`로 변경합니다.
- `imported_recipe_id`를 연결합니다.

## Reject

```text
POST /api/v1/admin/recipe-sources/{source_id}/reject
```

Request:

```json
{
  "reason": "원문 신뢰도가 낮음"
}
```

거절 사유는 `validation_errors` 또는 별도 review note에 기록할 수 있습니다.

## Retry

재처리 action:

- `retry-normalize`: raw payload에서 normalized payload 재생성
- `retry-images`: 원본 이미지 URL에서 S3 업로드 재시도

초기 구현에서는 retry action을 동기 처리해도 되지만, 대량 처리 시 background job으로 분리합니다.

## Generate Image

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations
```

요청 예시:

```json
{
  "reason": "기존 대표 이미지가 없음",
  "prompt_overrides": {
    "style": "realistic Korean food photography",
    "must_include": ["김치", "밥", "달걀 프라이"],
    "avoid": ["글자", "로고", "사람"]
  }
}
```

응답 예시:

```json
{
  "generation_id": 10,
  "recipe_id": 123,
  "status": "SUCCEEDED",
  "image_url": "https://s3.../main.jpg",
  "thumbnail_url": "https://s3.../thumb.jpg"
}
```

이 API는 기존 `recipes.image_url`을 바로 덮어쓰지 않습니다. 새 후보를 `recipe_image_generations`에 저장하고, 관리자가 선택했을 때만 대표 이미지로 반영합니다.

## Select Image

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
```

동작:

- 같은 레시피의 기존 `SELECTED` 후보를 `REJECTED`로 변경합니다.
- 선택한 후보를 `SELECTED`로 변경합니다.
- `recipes.image_url`, `recipes.thumbnail_url`, `recipes.image_urls`를 갱신합니다.

## Reject Image

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

마음에 들지 않는 후보는 `REJECTED`로 바꾸고, 필요하면 다시 `POST /image-generations`로 재생성합니다.
