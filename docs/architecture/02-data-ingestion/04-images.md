# 04. Image Storage

서비스에서 노출하는 이미지는 원본 외부 URL을 production media로 바로 사용하지 않습니다. 수집 source의 이미지 URL은 staging에 보관하고, 정식 레시피 이미지는 이후 AI 이미지 생성/선택 흐름으로 채웁니다.

## Policy

- 원본 이미지 URL은 `recipe_source_extractions`와 `recipe_source_extracted_steps`에 남깁니다.
- production import는 원본 이미지 URL을 `recipe_media`로 복사하지 않습니다.
- `recipes`에는 `image_url`, `thumbnail_url`, `image_urls` 같은 중복 컬럼을 두지 않습니다.
- 서비스 노출용 이미지는 AI 생성 후보를 만든 뒤 선택된 결과만 `recipe_media`에 저장합니다.
- AI로 생성한 이미지도 S3 같은 object storage에 업로드한 뒤 `recipe_media.storage_url`로 관리합니다.

## Image Roles

| Role | Meaning |
| --- | --- |
| `MAIN` | 서비스 대표 이미지 |
| `THUMBNAIL` | 목록, 카드, 검색 결과용 썸네일 |
| `STEP` | 특정 조리 단계 이미지 |
| `GALLERY` | 상세 화면 보조 이미지 |
| `GENERATED_CANDIDATE` | AI가 생성했지만 아직 선택되지 않은 후보 |

## Source Image Flow

```text
source image url
  -> store only in staging extraction fields
  -> do not create recipe_media during production import
```

## Generated Image Flow

```text
recipe without production image
  -> generate candidate image with AI
  -> upload generated image to S3
  -> create recipe_image_generations row
  -> create recipe_media row with GENERATED_CANDIDATE
  -> select candidate
  -> mark selected media as MAIN / THUMBNAIL
```

AI 생성 결과는 기본적으로 후보입니다. 생성 직후 서비스 대표 이미지로 바로 노출하지 않고, 선택된 뒤 `recipe_media` 역할을 변경합니다.

## S3 Key

AI 생성 이미지:

```text
recipes/generated/{recipe_id}/{generation_id}/main.jpg
recipes/generated/{recipe_id}/{generation_id}/thumb.jpg
```

## Metadata

`recipe_media`에는 파일 관리에 필요한 최소 메타데이터를 둡니다.

| Column | Meaning |
| --- | --- |
| `source_url` | provider 임시 URL 또는 추적용 URL |
| `storage_url` | S3 업로드 후 서비스에서 사용하는 URL |
| `thumbnail_url` | 별도 썸네일 파일이 있을 때의 URL |
| `width`, `height` | 이미지 크기 |
| `file_size_bytes` | 파일 크기 |
| `mime_type` | `image/jpeg`, `image/png` 등 |
| `storage_provider` | `S3`, `OPENAI`, 외부 이미지 출처 등 |
| `generation_id` | AI 생성 이력과의 연결 |

## Failure Handling

AI 이미지 생성 실패는 `recipe_image_generations.status = FAILED`로 남깁니다. 이후 다시 생성하거나 이미지 없이 레시피를 유지할 수 있습니다.