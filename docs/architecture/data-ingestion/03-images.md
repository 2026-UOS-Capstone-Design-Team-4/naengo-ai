# 03. Image Storage

서비스에서 노출하는 이미지는 원본 외부 URL을 직접 쓰지 않고 S3 같은 object storage에 업로드한 뒤 `recipe_media`에 저장합니다.

## Policy

- 원본 이미지 URL은 source/staging 영역에 남깁니다.
- 운영 이미지 URL은 `recipe_media.storage_url`에 저장합니다.
- 원본 URL은 추적을 위해 `recipe_media.source_url`에도 남길 수 있습니다.
- 대표 이미지, 썸네일, 단계 이미지는 모두 `recipe_media.image_role`로 구분합니다.
- `recipes`에는 `image_url`, `thumbnail_url`, `image_urls` 같은 중복 컬럼을 두지 않습니다.
- AI로 생성한 이미지도 S3에 업로드한 뒤 `recipe_media`로 관리합니다.

## Image Roles

| Role | Meaning |
| --- | --- |
| `MAIN` | 서비스 대표 이미지 |
| `THUMBNAIL` | 목록, 카드, 검색 결과용 썸네일 |
| `STEP` | 특정 조리 단계 이미지 |
| `SOURCE` | 원본 사이트에서 가져온 보조 이미지 |
| `GENERATED_CANDIDATE` | AI가 생성했지만 아직 선택되지 않은 후보 |

단계별 이미지는 `recipe_media.step_id`로 `recipe_steps`에 연결합니다. 한 단계에 이미지가 여러 장 필요하면 같은 `step_id`에 여러 media row를 저장하고 `sort_order`로 정렬합니다.

## Source Image Flow

```text
source image url
  -> download with rate limit
  -> validate content type and size
  -> upload to S3
  -> store storage_url in recipe_media
  -> keep original URL in source_url
```

## Generated Image Flow

```text
missing or unusable main image
  -> generate candidate image with AI
  -> upload generated image to S3
  -> create recipe_image_generations row
  -> create recipe_media row with GENERATED_CANDIDATE
  -> admin selects candidate
  -> mark selected media as MAIN / THUMBNAIL
```

AI 생성 결과는 기본적으로 후보입니다. 생성 직후 서비스 대표 이미지로 바로 노출하지 않고, 관리자가 선택한 뒤 `recipe_media` 역할을 변경합니다.

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

`recipe_media`에는 파일 관리에 필요한 최소 메타데이터를 둡니다.

| Column | Meaning |
| --- | --- |
| `source_url` | 원본 사이트 이미지 URL 또는 provider 임시 URL |
| `storage_url` | S3 업로드 후 서비스에서 사용하는 URL |
| `thumbnail_url` | 별도 썸네일 파일이 있을 때의 URL |
| `width`, `height` | 이미지 크기 |
| `file_size_bytes` | 파일 크기 |
| `mime_type` | `image/jpeg`, `image/png` 등 |
| `provider` | `S3`, `OPENAI`, 외부 이미지 출처 등 |
| `generation_id` | AI 생성 이력과의 연결 |

## Failure Handling

S3 업로드 실패 시 import 전체를 실패시키기보다 해당 media만 실패 상태로 남기고, 레시피는 검수 상태로 돌립니다.

AI 이미지 생성 실패는 `recipe_image_generations.status = FAILED`로 남깁니다. 관리자는 admin API에서 다시 생성할 수 있습니다.
