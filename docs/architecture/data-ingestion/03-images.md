# 03. Image Storage

서비스에 노출하는 이미지는 원본 외부 URL을 직접 사용하지 않고 S3에 업로드한 뒤 S3 URL을 저장합니다.

## Policy

- 원본 사이트의 이미지 URL은 `source_metadata`에 보관합니다.
- 서비스 대표 이미지는 `recipes.image_url`에 저장합니다.
- 서비스 썸네일은 `recipes.thumbnail_url`에 저장합니다.
- 전체 이미지 목록은 `recipes.image_urls`에 저장합니다.
- 단계별 이미지는 `recipe_steps.image_url`에 저장합니다.
- AI로 생성한 이미지도 S3에 업로드한 뒤 동일한 컬럼 규칙을 따릅니다.

## Source Image Flow

```text
source image url
  -> download with rate limit
  -> validate content type and size
  -> upload to S3
  -> store S3 URL in recipes / recipe_steps
  -> keep original URL in source_metadata
```

## Generated Image Flow

```text
missing or unusable main image
  -> generate candidate image with AI
  -> upload generated image to S3
  -> store candidate in recipe_image_generations
  -> admin selects candidate
  -> update recipes.image_url / thumbnail_url / image_urls
```

AI 생성 결과는 기본적으로 후보입니다. 생성 즉시 `recipes.image_url`을 덮어쓰지 않고, 관리자 선택 후에만 대표 이미지로 반영합니다.

## S3 Key

원본 이미지:

```text
recipes/{source_site}/{source_recipe_id}/main.jpg
recipes/{source_site}/{source_recipe_id}/thumb.jpg
recipes/{source_site}/{source_recipe_id}/steps/{step_no}.jpg
```

AI 생성 이미지:

```text
recipes/generated/{recipe_id}/{generation_id}/main.jpg
recipes/generated/{recipe_id}/{generation_id}/thumb.jpg
```

## Metadata

원본 URL은 다음 위치에 보관합니다.

```json
{
  "source_thumbnail_url": "https://...",
  "source_image_urls": ["https://..."],
  "source_step_images": ["https://..."]
}
```

생성 이미지의 프롬프트, 모델, provider, 실패 사유, 후보 URL은 `recipe_image_generations`에 저장합니다.

## Failure Handling

S3 업로드 실패 시 해당 `recipe_sources`는 `REVIEW_REQUIRED` 또는 별도 retry 대상으로 둡니다.

AI 이미지 생성 실패는 import 전체 실패로 보지 않습니다. `recipe_image_generations.status = FAILED`로 남기고, 관리자 API에서 재생성할 수 있게 합니다.
