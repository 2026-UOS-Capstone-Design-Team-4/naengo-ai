# 05. AI Image Generation

AI 이미지 생성은 production recipe import와 분리된 후속 작업이다. source 원본 이미지 URL은 참고 정보로만 남기고, 서비스에 노출할 이미지는 Naengo가 생성/선택/저장한 media만 사용한다.

## Goals

- 외부 원본 이미지 URL에 의존하지 않는 안정적인 서비스 이미지를 만든다.
- 생성 요청, prompt, provider, 실패 원인, 선택 여부를 `recipe_image_generations`에 남긴다.
- 실제 노출 media는 `recipe_media`에서 관리한다.
- 생성 파일은 provider 임시 URL이 아니라 S3 같은 object storage에 업로드한 뒤 사용한다.

## When To Generate

생성 대상:

- production recipe에 `MAIN` 또는 `THUMBNAIL` media가 없음
- source 이미지 URL만 있고 서비스 노출 media가 없음
- 운영자가 특정 recipe의 이미지 보강을 요청함
- 기존 생성 이미지 품질이 낮아 재생성이 필요함

생성하지 않는 대상:

- `review_status = REJECTED`였던 source에서 온 recipe
- 제목, 주요 재료, 완성 형태 설명이 부족한 recipe
- 중복 의심 또는 품질 검수가 끝나지 않은 recipe

## Status Flow

`recipe_image_generations.status`:

| Status | Meaning |
| --- | --- |
| `REQUESTED` | 생성 요청 row가 만들어짐 |
| `GENERATING` | provider 호출 또는 파일 처리 중 |
| `SUCCEEDED` | 이미지 생성과 storage 업로드가 끝남 |
| `FAILED` | provider, safety, upload, metadata 처리 중 실패 |
| `SELECTED` | 운영자가 해당 후보를 대표 이미지로 선택 |
| `REJECTED` | 운영자가 후보를 사용하지 않기로 함 |

이미지 파일이 DB에 있다는 사실만으로 “대표 이미지로 성공 반영됨”을 의미하지 않는다. 생성 성공은 `SUCCEEDED`, 서비스 노출 선택은 `SELECTED`와 `recipe_media.image_role = MAIN/THUMBNAIL`로 구분한다.

## Pipeline

```text
recipe without selected media
  -> build prompt from production recipe tables
  -> create recipe_image_generations(status = REQUESTED)
  -> call provider(status = GENERATING)
  -> upload generated file to S3
  -> create recipe_media(image_role = GENERATED_CANDIDATE)
  -> mark generation SUCCEEDED
  -> admin selects candidate
  -> mark selected media MAIN / THUMBNAIL
  -> mark generation SELECTED
```

`GENERATING`은 비동기 worker나 background job에서 유효하다. 동기 script가 요청부터 결과 저장까지 한 번에 처리한다면 DB에 `GENERATING`이 오래 남지 않을 수 있다.

## Prompt Inputs

Prompt는 production recipe의 정규화된 값으로 만든다.

```json
{
  "title": "김치볶음밥",
  "summary": "잘 익은 김치와 밥을 볶아 만든 한 그릇 요리",
  "main_ingredients": ["김치", "밥", "대파", "달걀"],
  "dish_type": "rice",
  "cooking_methods": ["stir_fry"],
  "servings": 1,
  "style": "realistic Korean home cooking food photography"
}
```

Prompt 원칙:

- 완성 음식이 잘 보이는 실제 음식 사진 스타일을 기본으로 한다.
- 레시피에 없는 핵심 재료를 임의로 추가하지 않는다.
- 로고, 글자, 워터마크, 사람 얼굴을 만들지 않는다.
- 조리 전 재료보다 완성 결과를 우선한다.

## Storage

생성 이미지는 provider 임시 URL에 의존하지 않고 object storage에 업로드한다.

```text
recipes/generated/{recipe_id}/{generation_id}/main.jpg
recipes/generated/{recipe_id}/{generation_id}/thumb.jpg
```

`recipe_media` 주요 값:

- `media_type = IMAGE`
- `image_role = GENERATED_CANDIDATE`, 선택 후 `MAIN` 또는 `THUMBNAIL`
- `source_url`: provider 임시 URL 또는 추적 URL
- `storage_url`: 서비스에서 사용하는 object storage URL
- `storage_provider = S3`
- `generation_id`: 생성 이력 연결

## Selection

후보 이미지를 선택할 때는 기존 대표 이미지를 덮어쓰기보다 역할을 조정한다.

```text
BEGIN
  previous MAIN -> GALLERY or archived policy
  selected GENERATED_CANDIDATE -> MAIN
  selected thumbnail -> THUMBNAIL
  generation.status -> SELECTED
COMMIT
```

## Failure Handling

| Failure | Handling |
| --- | --- |
| provider API 실패 | `recipe_image_generations.status = FAILED` |
| safety 거절 | `FAILED`와 `error_message` 기록 |
| S3 upload 실패 | media row를 만들지 않거나 candidate를 무효화 |
| prompt 정보 부족 | 생성 대상에서 제외 |
| 결과 품질 낮음 | `REJECTED`, 필요 시 새 generation 생성 |

이미지 생성 실패는 recipe import 실패로 간주하지 않는다. 이미지 없이도 recipe는 유지될 수 있다.

## Service Boundary

- `ImageGenerationService`: prompt 생성, provider 호출, generation row 관리
- `StorageService`: local/S3 저장소 차이를 숨기는 interface
- `AdminRecipeImageService`: 후보 목록, 선택, 거절
- `RecipeQueryService`: `recipe_media`에서 `MAIN`, `THUMBNAIL`을 찾아 응답 구성
