# 05. AI Image Generation

레시피에 대표 이미지가 없거나 이미지 품질이 낮은 경우 AI 이미지 생성으로 후보를 보완합니다. 생성은 수집 파이프라인과 연결되지만, 비용과 검수가 필요하므로 별도 서비스와 admin API로 분리합니다.

## Goals

- 원본 대표 이미지가 없을 때 서비스에 노출 가능한 후보 이미지를 생성합니다.
- 관리자가 생성 결과를 확인하고 마음에 들지 않으면 다시 생성할 수 있게 합니다.
- 최종 선택된 이미지만 `recipe_media`의 대표 이미지로 반영합니다.
- 생성 프롬프트, 모델, 실패 원인, 후보 media 연결은 `recipe_image_generations`에 남깁니다.

## When To Generate

자동 생성 대상:

- source extraction에 대표 이미지가 없음
- 원본 이미지 다운로드 또는 S3 업로드 실패
- 이미지가 너무 작거나 깨진 파일로 판정됨
- 관리자가 검수 중 대표 이미지 보완이 필요하다고 판단함

자동 생성하지 않는 대상:

- 저작권 또는 출처 검토가 끝나지 않은 레시피
- 제목, 주요 재료, 조리 결과 설명이 부족한 데이터
- 중복 후보 또는 `REJECTED` 상태 데이터

## Pipeline

```text
recipe source import
  -> no usable main image
  -> build image prompt from recipe tables
  -> call image generation provider
  -> upload generated image to S3
  -> create recipe_media with GENERATED_CANDIDATE
  -> create recipe_image_generations row
  -> admin selects image
  -> mark selected media as MAIN / THUMBNAIL
```

초기 구현에서는 import 중 자동 생성까지는 허용하되, 최종 반영은 관리자 선택 후 처리하는 것을 권장합니다.

## Prompt Inputs

프롬프트는 원문 전체가 아니라 운영 테이블의 정규화된 요약 데이터로 만듭니다.

```json
{
  "title": "김치볶음밥",
  "summary": "잘 익은 김치와 밥을 볶아 만든 한 그릇 요리",
  "main_ingredients": ["김치", "밥", "대파", "계란"],
  "cuisine_type": "korean",
  "dish_type": "rice",
  "cooking_method": "stir_fry",
  "servings": 1,
  "style": "realistic food photography"
}
```

프롬프트 정책:

- 실제 음식 사진처럼 보이는 구도를 기본값으로 합니다.
- 브랜드 로고, 사람 얼굴, 글자, 워터마크는 생성하지 않습니다.
- 조리 전 재료보다 완성된 요리를 우선합니다.
- 레시피에 없는 핵심 재료를 임의로 추가하지 않습니다.

## Storage

생성된 파일은 provider URL을 직접 쓰지 않고 S3에 업로드합니다.

```text
recipes/generated/{recipe_id}/{generation_id}/main.jpg
recipes/generated/{recipe_id}/{generation_id}/thumb.jpg
```

저장 위치:

- `recipe_image_generations`: 생성 요청과 결과 이력
- `recipe_media`: 실제 서비스 이미지 후보와 최종 선택 이미지

`recipes`에는 이미지 URL을 저장하지 않습니다. 조회 API는 `recipe_media`에서 `MAIN`, `THUMBNAIL` 역할을 찾아 응답합니다.

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
    "must_include": ["김치", "계란 프라이"],
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
  "media_id": 55,
  "storage_url": "https://s3.../main.jpg",
  "thumbnail_url": "https://s3.../thumb.jpg"
}
```

재생성은 기존 대표 이미지를 덮어쓰지 않습니다. 후보를 만들고 관리자가 선택할 때만 `recipe_media` 역할이 변경됩니다.

## Selection API

```text
GET  /api/v1/admin/recipes/{recipe_id}/image-generations
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/select
POST /api/v1/admin/recipes/{recipe_id}/image-generations/{generation_id}/reject
```

선택 처리:

```text
BEGIN
  UPDATE previous MAIN media -> SOURCE or archive flag
  UPDATE selected candidate media -> MAIN
  UPDATE selected thumbnail media -> THUMBNAIL
  UPDATE recipe_image_generations.status -> SELECTED
COMMIT
```

## Failure Handling

| Failure | Handling |
| --- | --- |
| provider API 실패 | `recipe_image_generations.status = FAILED` |
| S3 업로드 실패 | 후보 media 생성 실패로 처리하고 retry 가능하게 남김 |
| 부적절한 이미지 | 관리자가 `REJECTED` 처리 |
| 비용 한도 초과 | 생성 요청 거절 또는 queue 대기 |
| 프롬프트 정보 부족 | `parse_status = REVIEW_REQUIRED`로 돌려 관리자 보완 요청 |

## Service Boundary

- `ImageGenerationService`: 프롬프트 생성, provider 호출, S3 업로드, 생성 이력 저장
- `RecipeImportService`: 대표 이미지가 없을 때 생성 후보 요청을 트리거
- `AdminRecipeImageService`: 후보 목록, 선택, 거절 처리
- `RecipeQueryService`: `recipe_media`를 조합해 최종 조회 응답 생성

이렇게 나누면 추천/조회 API 응답 시간이 AI 이미지 생성 비용과 지연에 묶이지 않습니다.
