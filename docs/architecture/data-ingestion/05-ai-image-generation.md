# 05. AI Image Generation

레시피 대표 이미지가 없거나 품질이 낮은 경우 AI 이미지 생성으로 보완합니다. 이 기능은 수집 파이프라인과 연결되지만, 비용과 품질 검수가 필요하므로 별도 서비스와 관리자 API로 분리합니다.

## Goals

- 원본 대표 이미지가 없을 때 서비스에 노출할 수 있는 대표 이미지 후보를 생성합니다.
- 관리자가 생성 결과를 확인하고 마음에 들지 않으면 다시 생성할 수 있게 합니다.
- 최종 선택된 이미지만 `recipes.image_url`, `recipes.thumbnail_url`, `recipes.image_urls`에 반영합니다.
- 생성 프롬프트, 모델, 실패 원인, 후보 URL은 `recipe_image_generations`에 이력으로 남깁니다.

## When To Generate

자동 생성 대상:

- `normalized_payload.recipe.image_url`이 비어 있음
- 원본 이미지 다운로드 또는 S3 업로드 실패
- 이미지가 너무 작거나 깨진 파일로 판정됨
- 관리자 검수에서 대표 이미지 보완이 필요하다고 판단됨

자동 생성하지 않는 대상:

- 저작권 또는 출처 검토가 끝나지 않은 레시피
- 레시피 제목, 주요 재료, 조리 결과 설명이 부족한 데이터
- 중복 후보 또는 `REJECTED` 상태 데이터

## Pipeline

```text
recipe source import
  -> no usable main image
  -> build image prompt from normalized recipe data
  -> call image generation provider
  -> upload generated image to S3
  -> create recipe_image_generations row
  -> mark candidate as SUCCEEDED
  -> admin selects image
  -> update recipes.image_url / thumbnail_url / image_urls
```

초기 구현에서는 import 중 자동 생성까지는 하되, 최종 반영은 관리자 선택 후 처리하는 것을 권장합니다. 이렇게 하면 AI 이미지가 의도와 다르게 생성됐을 때 서비스에 바로 노출되는 위험을 줄일 수 있습니다.

## Prompt Inputs

프롬프트는 레시피 원문 전체가 아니라 정규화된 요약 데이터로 만듭니다.

```json
{
  "title": "김치볶음밥",
  "summary": "매콤한 김치와 밥을 볶아 만든 한 그릇 요리",
  "main_ingredients": ["김치", "밥", "대파", "달걀"],
  "cuisine_type": "korean",
  "dish_type": "rice",
  "cooking_method": "stir_fry",
  "servings": 1,
  "style": "realistic food photography"
}
```

프롬프트 정책:

- 실제 음식 사진처럼 보이는 구도를 기본값으로 합니다.
- 브랜드 로고, 사람 얼굴, 텍스트, 워터마크는 생성하지 않습니다.
- 조리 전 재료보다 완성된 요리를 우선합니다.
- 레시피에 없는 핵심 재료를 임의로 추가하지 않습니다.

## Storage

생성된 파일도 외부 provider URL을 직접 쓰지 않고 S3에 업로드합니다.

```text
recipes/generated/{recipe_id}/{generation_id}/main.jpg
recipes/generated/{recipe_id}/{generation_id}/thumb.jpg
```

최종 선택본:

- `recipes.image_url`: 선택된 대표 이미지 S3 URL
- `recipes.thumbnail_url`: 선택된 썸네일 S3 URL
- `recipes.image_urls`: 대표 이미지 후보 또는 추가 이미지 목록

생성 이력:

- `recipe_image_generations.image_url`
- `recipe_image_generations.thumbnail_url`
- `recipe_image_generations.prompt`
- `recipe_image_generations.provider`
- `recipe_image_generations.model`
- `recipe_image_generations.status`
- `recipe_image_generations.metadata`

## Regeneration

관리자는 생성 이미지가 마음에 들지 않을 때 다시 생성할 수 있습니다.

```text
POST /api/v1/admin/recipes/{recipe_id}/image-generations
```

요청 예시:

```json
{
  "reason": "음식이 실제 김치볶음밥처럼 보이지 않음",
  "prompt_overrides": {
    "style": "realistic Korean home cooking photo",
    "must_include": ["김치", "달걀 프라이"],
    "avoid": ["치즈", "고기"]
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

재생성은 기존 이미지를 덮어쓰지 않습니다. 새 후보를 만들고 관리자가 선택할 때만 `recipes.image_url`을 갱신합니다.

## Selection API

```text
GET  /api/v1/admin/recipes/{recipe_id}/image-generations
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

선택 처리:

```text
BEGIN
  UPDATE previous selected generation -> REJECTED
  UPDATE selected generation -> SELECTED
  UPDATE recipes.image_url / thumbnail_url / image_urls
COMMIT
```

## Failure Handling

| Failure | Handling |
| --- | --- |
| provider API 실패 | `recipe_image_generations.status = FAILED` |
| S3 업로드 실패 | 생성 결과를 선택 불가 처리하고 retry 가능하게 둠 |
| 부적절한 이미지 | 관리자가 `REJECTED` 처리 |
| 비용 한도 초과 | 생성 요청 거절 또는 queue 대기 |
| 프롬프트 정보 부족 | `REVIEW_REQUIRED`로 돌려 관리자 보완 요청 |

## Service Boundary

추천 서비스나 일반 레시피 조회 API는 이미지 생성 provider를 직접 호출하지 않습니다.

- `ImageGenerationService`: 프롬프트 생성, provider 호출, S3 업로드, 이력 저장
- `RecipeImportService`: 대표 이미지가 없을 때 생성 요청을 트리거
- `AdminRecipeImageService`: 재생성, 후보 목록, 선택, 거절 처리
- `RecipeService`: 최종 선택된 `recipes.image_url`만 읽음

이렇게 나누면 추천/조회 API 응답 시간이 AI 이미지 생성 비용과 지연에 묶이지 않습니다.
