# 02. Admin API

Admin API는 운영자 화면에서 사용하는 API입니다. 검수, 승인, import, AI 보정, AI 이미지 생성, 재처리를 담당합니다.

## Recipe Sources

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

## Admin Recipes

```text
GET    /api/v1/admin/recipes
GET    /api/v1/admin/recipes/{recipe_id}
PATCH  /api/v1/admin/recipes/{recipe_id}
POST   /api/v1/admin/recipes/{recipe_id}/activate
POST   /api/v1/admin/recipes/{recipe_id}/deactivate
POST   /api/v1/admin/recipes/{recipe_id}/refresh-embedding
```

관리자 레시피 API는 서비스 노출 여부, 메타데이터 보정, 검색 품질 개선을 다룹니다.

## AI Image Generations

```text
GET    /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST   /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

AI 이미지 생성은 비용이 크고 관리자의 시각 검수가 필요하므로 생성 후보를 DB에 저장합니다. 선택 API가 호출된 경우에만 `recipes.image_url`을 갱신합니다.

## Pending Recipes

```text
GET    /api/v1/admin/pending-recipes
GET    /api/v1/admin/pending-recipes/{pending_recipe_id}
PATCH  /api/v1/admin/pending-recipes/{pending_recipe_id}
POST   /api/v1/admin/pending-recipes/{pending_recipe_id}/approve
POST   /api/v1/admin/pending-recipes/{pending_recipe_id}/reject
POST   /api/v1/admin/pending-recipes/{pending_recipe_id}/enrich
```

사용자 제출 레시피는 관리자가 내용을 보완한 뒤 승인하거나 거절합니다.

## Pending Recipe AI Enrichment

사용자가 올린 `pending_recipes`는 일부 컬럼이 비어 있을 수 있습니다. 관리자는 AI 보정 API로 다른 컬럼을 참고해 빈 값을 채울 수 있는 `suggested_patch`를 받아옵니다.

AI 보정 결과는 DB에 저장하지 않습니다. 프론트가 응답을 미리보기로 보여주고, 관리자가 마음에 들면 기존 `PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}`로 반영합니다.

대상 필드 예시:

- `description`
- `ingredients`
- `ingredients_raw`
- `instructions`
- `servings`
- `cooking_time`
- `calories`
- `difficulty`
- `category`
- `tags`
- `tips`

생성 요청:

```text
POST /api/v1/admin/pending-recipes/{pending_recipe_id}/enrich
```

요청 예시:

```json
{
  "target_fields": ["ingredients", "instructions", "difficulty", "tags"],
  "mode": "missing_only",
  "admin_instruction": "사용자가 쓴 content를 기준으로 과장하지 말고 빈 값만 채워줘."
}
```

응답 예시:

```json
{
  "pending_recipe_id": 31,
  "mode": "missing_only",
  "suggested_patch": {
    "ingredients": [
      {"name": "김치", "amount": "1", "unit": "컵"},
      {"name": "밥", "amount": "1", "unit": "공기"}
    ],
    "difficulty": "easy",
    "tags": ["한그릇", "김치", "볶음밥"]
  },
  "confidence": {
    "ingredients": 0.82,
    "difficulty": 0.74,
    "tags": 0.88
  },
  "warnings": []
}
```

적용 요청:

```text
PATCH /api/v1/admin/pending-recipes/{pending_recipe_id}
```

프론트는 `suggested_patch`를 수정 가능한 폼에 채우고, 관리자가 저장을 누르면 기존 수정 API로 보냅니다.

저장 정책:

- AI 보정 patch는 기본적으로 DB에 저장하지 않습니다.
- 서버 로그에는 요청 시간, 관리자 id, 대상 pending recipe id, target fields, 성공/실패 정도만 남깁니다.
- prompt, input snapshot, suggested patch는 초기에 저장하지 않습니다.
- 보정 이력이 필요해지면 audit log 또는 object storage 기반으로 별도 설계합니다.

## Scraper Operations

```text
GET    /api/v1/admin/scraper-runs
GET    /api/v1/admin/scraper-runs/{run_id}
POST   /api/v1/admin/scraper-runs
POST   /api/v1/admin/scraper-runs/{run_id}/cancel
```

초기에는 `scraper_runs` 테이블 없이 logs와 `recipe_sources` 상태로 운영할 수 있습니다. 운영 화면에서 run 단위 추적이 필요해지면 테이블을 추가합니다.

## Admin Permissions

Admin API는 `ADMIN` 권한을 요구합니다. 로그인 고도화 전에는 임시 보호 장치를 둘 수 있지만, API contract는 role 기반 권한을 전제로 합니다.
