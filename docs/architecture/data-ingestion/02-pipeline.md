# 02. Data Ingestion Pipeline

## Import Flow

```text
1. scraper가 raw payload를 만든다.
2. recipe_sources에 COLLECTED 상태로 저장한다.
3. normalizer가 공통 ingestion JSON으로 변환한다.
4. validator가 필수 필드와 enum 값을 검증한다.
5. duplicate checker가 중복을 판정한다.
6. 원본 이미지를 다운로드하고 S3에 업로드한다.
7. 대표 이미지가 없거나 사용할 수 없으면 AI 이미지 생성 후보를 만든다.
8. READY 데이터만 recipes, recipe_ingredients, recipe_steps로 import한다.
9. recipe_stats row와 embedding을 생성한다.
10. recipe_sources.status를 IMPORTED로 변경하고 imported_recipe_id를 연결한다.
```

## Status

| Status | Meaning |
| --- | --- |
| `COLLECTED` | 원천 데이터를 수집함 |
| `PARSED` | 공통 포맷으로 정규화됨 |
| `INVALID` | 필수 필드 부족 또는 파싱 실패 |
| `DUPLICATE` | 중복으로 판단됨 |
| `READY` | import 가능 |
| `REVIEW_REQUIRED` | 사람이 확인해야 함 |
| `IMPORTED` | 정식 `recipes`로 승격됨 |
| `REJECTED` | 사용하지 않기로 결정 |

## Auto Import Conditions

- 제목, 설명, 재료, 조리 단계가 있음
- 인분, 조리 시간, 난이도, 카테고리가 있음
- 출처 URL이 있음
- 중복이 아님
- `difficulty`가 `easy`, `normal`, `hard` 중 하나로 정규화됨

대표 이미지는 자동 import의 필수 조건으로 두지 않습니다. 이미지가 없으면 import 후 AI 이미지 후보를 만들고 관리자 선택을 기다립니다.

## Review Required Conditions

- 원문 조리 순서를 그대로 서비스에 노출하기 어려운 경우
- 이미지 사용 정책 확인이 필요한 경우
- 중복 가능성이 높은 경우
- 카테고리나 태그 정규화에 실패한 경우
- 재료 파싱 신뢰도가 낮은 경우
- AI 이미지 생성을 위한 프롬프트 정보가 부족한 경우

## Deduplication

판단 순서:

1. `source_url`
2. `source_site + source_recipe_id`
3. `content_hash`
4. `title + main_ingredients`
5. embedding similarity
6. `REVIEW_REQUIRED`

## Image Handling

원본 이미지가 있으면 S3 업로드를 우선합니다. 원본 이미지가 없거나 사용할 수 없으면 `ImageGenerationService`가 대표 이미지 후보를 생성합니다.

```text
source image exists
  -> download and upload to S3
  -> recipes.image_url

source image missing
  -> generate AI image candidate
  -> recipe_image_generations
  -> admin select
  -> recipes.image_url
```

## Legacy JSON

`db/samples/legacy_youtube_recipes.json`은 기본 import에서 제외합니다. 필요한 경우 `scripts/legacy/import_youtube_recipes.py`로 처리하되, 새 ingestion의 메인 파이프라인과는 분리합니다.

## Background Job 처리

각 단계(스크래핑, 정규화, import)의 실행 방식과 실패/재시도 정책은 [Background Jobs](../../background-jobs/00-overview.md)를 참고합니다.
