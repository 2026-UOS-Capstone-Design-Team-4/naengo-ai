# 02. Review API

Admin Review API는 수집된 `recipe_sources`와 추출 staging 데이터를 검수하고, 운영 레시피로 import하는 흐름을 제공합니다.

## Recipe Source Endpoints

```text
GET    /api/v1/admin/recipe-sources
GET    /api/v1/admin/recipe-sources/{source_id}
PATCH  /api/v1/admin/recipe-sources/{source_id}
POST   /api/v1/admin/recipe-sources/{source_id}/parse
POST   /api/v1/admin/recipe-sources/{source_id}/approve
POST   /api/v1/admin/recipe-sources/{source_id}/reject
POST   /api/v1/admin/recipe-sources/{source_id}/import
```

## Image Generation Endpoints

```text
GET    /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

이미지 생성은 비용과 검수 책임이 있으므로 일반 사용자 API가 아니라 admin API에서만 실행합니다.

## List Query

```text
GET /api/v1/admin/recipe-sources?collection_status=COLLECTED&parse_status=PARSED&review_status=PENDING&source_site=10000recipe&limit=50&cursor=...
```

Query params:

- `source_site`
- `source_type`
- `parser_type`
- `collection_status`
- `parse_status`
- `review_status`
- `import_status`
- `has_errors`
- `cursor`
- `limit`

## Detail Response

상세 조회는 원본과 추출 결과를 함께 내려줍니다. 관리 화면은 이 응답만으로 원문 확인, 추출값 수정, 승인 여부 판단을 할 수 있어야 합니다.

```json
{
  "source": {
    "id": 1,
    "source_site": "10000recipe",
    "source_url": "https://www.10000recipe.com/recipe/...",
    "collection_status": "COLLECTED",
    "parse_status": "PARSED",
    "review_status": "PENDING",
    "import_status": "NOT_IMPORTED"
  },
  "extraction": {
    "title": "한우 육회",
    "summary": "집에서 만드는 육회",
    "servings": 4,
    "cooking_time_minutes": 30,
    "main_image_source_url": "https://..."
  },
  "ingredients": [
    {
      "name": "소고기 홍두깨살",
      "amount_text": "300g",
      "sort_order": 1
    }
  ],
  "steps": [
    {
      "step_no": 1,
      "instruction": "고기를 키친타월로 눌러 핏물을 제거한다.",
      "source_image_url": "https://..."
    }
  ],
  "labels": [
    {
      "label_type": "TAG",
      "value": "육회",
      "source": "SCRAPE"
    }
  ]
}
```

## Patch Extraction

`PATCH`는 운영 테이블을 직접 수정하지 않고 추출 staging 값을 수정합니다.

```json
{
  "extraction": {
    "title": "집에서 만드는 한우 육회",
    "difficulty": "EASY"
  },
  "ingredients": [
    {
      "name": "소고기 홍두깨살",
      "amount_text": "300g",
      "sort_order": 1
    }
  ],
  "labels": [
    {
      "label_type": "CATEGORY",
      "value": "무침",
      "source": "ADMIN"
    }
  ]
}
```

## Parse

```text
POST /api/v1/admin/recipe-sources/{source_id}/parse
```

동작:

- `recipe_sources.raw_payload`를 다시 읽습니다.
- `recipe_source_extractions`, `recipe_source_extracted_ingredients`, `recipe_source_extracted_steps`, `recipe_source_extracted_labels`를 갱신합니다.
- 필수값 누락이나 파싱 실패는 `validation_errors`와 `parse_status`에 남깁니다.

## Approve

```text
POST /api/v1/admin/recipe-sources/{source_id}/approve
```

동작:

- 추출 staging validation을 다시 수행합니다.
- 문제가 없으면 `review_status = APPROVED`로 변경합니다.
- 자동 import는 하지 않습니다.

## Import

```text
POST /api/v1/admin/recipe-sources/{source_id}/import
```

동작:

- `APPROVED` source만 import합니다.
- `recipes`, `recipe_ingredients`, `recipe_steps`, `recipe_labels`, `recipe_classifications`, `recipe_media`를 생성합니다.
- embedding은 `recipe_embeddings`에 별도로 생성하거나 background job으로 넘깁니다.
- 원본 이미지가 없으면 AI 이미지 생성 후보를 만들 수 있지만, 바로 대표 이미지로 확정하지 않습니다.
- 성공하면 `recipe_sources.import_status = IMPORTED`로 변경하고 `imported_recipe_id`를 연결합니다.

## Reject

```text
POST /api/v1/admin/recipe-sources/{source_id}/reject
```

Request:

```json
{
  "reason": "원문 품질이 낮고 필수 조리 단계가 부족함"
}
```

거절 사유는 `validation_errors` 또는 별도 review note에 남길 수 있습니다.

## Select Image

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
```

동작:

- 같은 레시피의 기존 선택 후보를 `REJECTED`로 변경합니다.
- 선택 후보를 `SELECTED`로 변경합니다.
- 생성된 이미지를 `recipe_media`의 `MAIN`, `THUMBNAIL` 역할로 반영합니다.
- `recipes`에는 이미지 URL을 중복 저장하지 않습니다.

## Reject Image

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

마음에 들지 않는 후보는 `REJECTED`로 바꾸고, 필요하면 `POST /image-generations`로 다시 생성합니다.
