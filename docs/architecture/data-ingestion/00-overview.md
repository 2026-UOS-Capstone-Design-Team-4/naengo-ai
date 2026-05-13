# 00. Data Ingestion Overview

외부 레시피 데이터를 수집해 Naengo AI의 정식 레시피 데이터로 승격하는 설계입니다.

이번 구조에서는 `normalized_payload`, `normalized_metadata`를 중심으로 두지 않습니다. 원본은 `recipe_sources.raw_payload`에 보관하고, 파싱된 후보는 명시적인 staging 테이블에 저장한 뒤, 검수/승인 후 정식 레시피 테이블로 복사합니다.

## Primary Source

초기 데이터는 만개의레시피 스크래핑 결과를 기준으로 채웁니다.

```text
source_type = WEB_SCRAPE
source_site = 10000recipe
parser_type = HTML
```

## Legacy Source

`db/samples/legacy_youtube_recipes.json`는 YouTube 영상을 AI로 분석해 만든 기존 샘플 데이터입니다. 기본 import 대상에서는 제외하고 legacy sample로 보관합니다.

```text
source_type = VIDEO
source_site = youtube
parser_type = AI
```

## Flow

```text
10000recipe scrape
  -> recipe_sources.raw_payload
  -> recipe_source_extractions
  -> recipe_source_extracted_ingredients
  -> recipe_source_extracted_steps
  -> recipe_source_extracted_labels
  -> admin review
  -> recipes
  -> recipe_ingredients
  -> recipe_steps
  -> recipe_labels
  -> recipe_classifications
  -> recipe_media
  -> recipe_embeddings
```

## Table Roles

- `recipe_sources`: 외부 원본, 출처, 수집/파싱/검수/import 상태
- `recipe_source_extractions`: 정식 레시피가 되기 전의 파싱 후보 본문
- `recipe_source_extracted_ingredients`: 파싱 후보 재료
- `recipe_source_extracted_steps`: 파싱 후보 조리 단계
- `recipe_source_extracted_labels`: 파싱 후보 태그, 팁, 카테고리, 경고 문구
- `recipes`: 서비스에 노출하는 정식 레시피 본문
- `recipe_ingredients`: 검색 가능한 정규화 재료
- `recipe_steps`: 단계별 조리 설명
- `recipe_labels`: 태그, 팁, 카테고리, 경고 문구
- `recipe_classifications`: 추천/검색용 분류 축
- `recipe_media`: 대표 이미지, 썸네일, 단계 이미지, 갤러리 이미지
- `recipe_embeddings`: 벡터 검색용 embedding

## Terms

- `SCRAPE`: 웹에서 데이터를 수집하는 행위
- `SCRAP`: 사용자가 레시피를 저장하는 서비스 기능
- `raw_payload`: 원본 사이트에서 받은 데이터를 재파싱 가능하게 보관한 JSON
- `extraction`: raw payload에서 추출한 검수 후보값
- `classification`: 추천/검색에 쓰는 의미 기반 분류값

## Subdocuments

- [01. Schema](01-schema.md)
- [02. Pipeline](02-pipeline.md)
- [03. Image Storage](03-images.md)
- [04. Scraper Operations](04-scraper-operations.md)
- [05. AI Image Generation](05-ai-image-generation.md)
