# 02. Admin API

Admin API는 운영 화면에서 사용하는 관리용 API입니다. 수집 데이터 검수, 운영 레시피 관리, AI 보정, AI 이미지 생성, scraper 운영을 담당합니다.

## Recipe Sources

```text
GET    /api/v1/admin/recipe-sources
GET    /api/v1/admin/recipe-sources/{source_id}
PATCH  /api/v1/admin/recipe-sources/{source_id}
POST   /api/v1/admin/recipe-sources/{source_id}/parse
POST   /api/v1/admin/recipe-sources/{source_id}/approve
POST   /api/v1/admin/recipe-sources/{source_id}/reject
POST   /api/v1/admin/recipe-sources/{source_id}/import
```

`recipe_sources`는 원본 수집 이력이고, 실제 검수 대상 값은 `recipe_source_extractions` 계열 staging 테이블에 저장됩니다.

## Admin Recipes

```text
GET    /api/v1/admin/recipes
GET    /api/v1/admin/recipes/{recipe_id}
PATCH  /api/v1/admin/recipes/{recipe_id}
POST   /api/v1/admin/recipes/{recipe_id}/activate
POST   /api/v1/admin/recipes/{recipe_id}/deactivate
POST   /api/v1/admin/recipes/{recipe_id}/refresh-embedding
```

관리자는 서비스 노출 여부, 메타데이터 보정, 검색 색인 갱신을 수행합니다. 대표 이미지와 썸네일은 `recipes`가 아니라 `recipe_media`에서 조회합니다.

## AI Image Generations

```text
GET    /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

AI 이미지 생성은 후보를 `recipe_image_generations`에 저장합니다. 관리자가 선택한 후보만 `recipe_media`의 대표 이미지로 반영합니다.

## Pending Recipes

```text
GET    /api/v1/admin/pending-recipes
GET    /api/v1/admin/pending-recipes/{pending_recipe_id}
PATCH  /api/v1/admin/pending-recipes/{pending_recipe_id}
POST   /api/v1/admin/pending-recipes/{pending_recipe_id}/approve
POST   /api/v1/admin/pending-recipes/{pending_recipe_id}/reject
POST   /api/v1/admin/pending-recipes/{pending_recipe_id}/enrich
```

사용자가 제출한 레시피는 관리자가 내용을 보완한 뒤 승인하거나 거절합니다.

## Pending Recipe AI Enrichment

사용자가 올린 `pending_recipes`에는 일부 컬럼이 비어 있을 수 있습니다. 관리자는 AI 보정 API로 다른 컬럼을 참고해 빈 값을 채울 수 있는 `suggested_patch`를 응답으로 받습니다.

AI 보정 결과는 기본적으로 DB에 저장하지 않습니다. 프론트엔드가 응답을 미리보기로 보여주고, 관리자가 마음에 들면 기존 `PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}`로 반영합니다.

대상 필드 예시:

- `title`
- `summary`
- `description`
- `servings`
- `cooking_time_minutes`
- `calories`
- `difficulty`
- `ingredients`
- `steps`
- `labels`

생성 요청:

```text
POST /api/v1/admin/pending-recipes/{pending_recipe_id}/enrich
```

요청 예시:

```json
{
  "target_fields": ["ingredients", "steps", "difficulty", "labels"],
  "mode": "missing_only",
  "admin_instruction": "사용자가 쓴 내용을 과장하지 말고 빈 값만 채워줘"
}
```

응답 예시:

```json
{
  "pending_recipe_id": 31,
  "mode": "missing_only",
  "suggested_patch": {
    "ingredients": [
      {
        "name": "김치",
        "amount_text": "1컵",
        "sort_order": 1
      }
    ],
    "difficulty": "EASY",
    "labels": [
      {
        "label_type": "TAG",
        "value": "김치볶음밥"
      }
    ]
  },
  "confidence": {
    "ingredients": 0.82,
    "difficulty": 0.74,
    "labels": 0.88
  },
  "warnings": []
}
```

적용 요청:

```text
PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}
```

정책:

- AI 보정 patch는 기본적으로 DB에 저장하지 않습니다.
- 서버 로그에는 요청 시각, 관리자 id, 대상 pending recipe id, target fields, 성공/실패 정도만 남깁니다.
- prompt, input snapshot, suggested patch는 초기에는 저장하지 않습니다.
- 보정 이력이 필요해지면 audit log 또는 object storage 기반으로 별도 설계합니다.

## Scraper Operations

```text
GET    /api/v1/admin/scraper-runs
GET    /api/v1/admin/scraper-runs/{run_id}
POST   /api/v1/admin/scraper-runs
POST   /api/v1/admin/scraper-runs/{run_id}/cancel
```

초기에는 `scraper_runs` 테이블 없이 CLI 로그와 `recipe_sources` 상태로 운영할 수 있습니다. 운영 화면에서 run 단위 추적이 필요해지면 별도 테이블을 추가합니다.

## Admin Permissions

Admin API는 `ADMIN` 권한을 요구합니다. 로그인 고도화 전까지는 API contract상 role 기반 권한을 전제로 둡니다.
