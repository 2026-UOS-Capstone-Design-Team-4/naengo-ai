# 02. Data Ingestion Pipeline

## Import Flow

```text
1. scraper가 source page에서 raw payload를 만든다.
2. recipe_sources에 raw_payload와 출처 정보를 저장한다.
3. parser가 raw_payload를 extraction tables로 변환한다.
4. validator가 extraction 필수 필드와 enum 값을 검증한다.
5. duplicate checker가 source/content/title/embedding 기준으로 중복을 판정한다.
6. admin review에서 extraction 후보를 확인하고 수정한다.
7. 승인된 extraction만 production tables로 import한다.
8. 이미지 원본을 S3에 업로드하고 recipe_media에 저장한다.
9. 추천/검색용 recipe_classifications를 생성한다.
10. recipe_embeddings를 생성한다.
11. recipe_sources.import_status와 imported_recipe_id를 갱신한다.
```

## Lifecycle Fields

`recipe_sources`에는 단일 `status` 대신 역할별 상태를 둡니다.

| Field | Values | Purpose |
| --- | --- | --- |
| `collection_status` | `COLLECTED`, `FAILED`, `SKIPPED` | 원본 수집 결과 |
| `parse_status` | `NOT_PARSED`, `PARSED`, `INVALID`, `DUPLICATE`, `REVIEW_REQUIRED` | 파싱/검증 결과 |
| `review_status` | `PENDING`, `APPROVED`, `REJECTED` | 관리자 검수 결과 |
| `import_status` | `NOT_IMPORTED`, `IMPORTED`, `FAILED` | 정식 테이블 import 결과 |

## Import Conditions

- extraction에 `title`, `description`, `ingredients`, `steps`가 있음
- `servings`, `total_time_minutes`, `difficulty`가 있음
- source URL이 있음
- 중복이 아님
- 관리자 검수 상태가 `APPROVED`
- import 상태가 `NOT_IMPORTED`

대표 이미지는 import의 필수 조건으로 보지 않습니다. 원본 이미지가 없으면 import 후 AI 이미지 후보를 만들고 관리자 선택을 기다립니다.

## Review Required Conditions

- 원문 조리 순서를 그대로 서비스에 노출하기 어려운 경우
- 이미지 사용 정책 확인이 필요한 경우
- 중복 가능성이 높은 경우
- 카테고리나 태그 분류 신뢰도가 낮은 경우
- 재료 파싱 신뢰도가 낮은 경우
- AI 이미지 생성을 위한 프롬프트 정보가 부족한 경우

## Deduplication

판단 순서:

1. `source_url`
2. `source_site + source_recipe_id`
3. `raw_content_hash`
4. `recipe_source_extractions.content_hash`
5. `title + normalized ingredients`
6. embedding similarity
7. `parse_status = REVIEW_REQUIRED`

## Image Handling

이미지는 recipe 본문 컬럼에 직접 넣지 않고 `recipe_media`에 저장합니다.

```text
source image exists
  -> download
  -> upload to S3
  -> recipe_media(image_role = MAIN, is_primary = true)

source image missing
  -> generate AI image candidate
  -> recipe_image_generations
  -> recipe_media(image_role = GENERATED_CANDIDATE)
  -> admin select
  -> recipe_media(image_role = MAIN, is_primary = true)
```

## Legacy JSON

`db/samples/legacy_youtube_recipes.json`는 기본 import에서 제외합니다. 필요한 경우 `scripts/legacy/import_youtube_recipes.py`로 처리하되, 새 ingestion 메인 파이프라인과는 분리합니다.

## Background Job 처리

각 단계의 실행 방식과 실패/재시도 정책은 [Background Jobs](../../background-jobs/00-overview.md)를 참고합니다.
