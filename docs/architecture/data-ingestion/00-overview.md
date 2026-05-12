# 00. Data Ingestion Overview

외부 레시피 데이터를 수집해 Naengo AI 추천 DB로 가져오는 설계입니다.

## Primary Source

초기 데이터는 만개의레시피 스크래핑 결과를 기준으로 채웁니다.

```text
source_type = WEB_SCRAPE
source_site = 10000recipe
parser_type = HTML
```

## Legacy Source

`db/samples/legacy_youtube_recipes.json`는 YouTube 영상을 AI로 분석해 만든 기존 샘플 데이터입니다. 양이 적고 메타데이터가 부족하므로 기본 import 대상에서는 제외하고 legacy sample로 보관합니다.

```text
source_type = VIDEO
source_site = youtube
parser_type = AI
```

## Flow

```text
10000recipe scrape
  -> recipe_sources
  -> normalize / validate / deduplicate
  -> image download or AI image generation
  -> recipes
  -> recipe_ingredients
  -> recipe_steps
  -> recipe_stats
  -> embedding
```

## Terms

- `SCRAPE`: 웹에서 데이터를 수집하는 행위
- `SCRAP`: 사용자가 레시피를 저장하는 서비스 기능
- `source_metadata`: 외부 사이트 원본 값을 보관한 메타데이터
- `normalized_metadata`: 요리 추천/검색 기준으로 정규화한 메타데이터

## Subdocuments

- [01. Schema](01-schema.md)
- [02. Pipeline](02-pipeline.md)
- [03. Image Storage](03-images.md)
- [04. Scraper Operations](04-scraper-operations.md)
- [05. AI Image Generation](05-ai-image-generation.md)
