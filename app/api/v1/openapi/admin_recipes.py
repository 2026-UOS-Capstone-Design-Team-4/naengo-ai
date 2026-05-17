from app.api.v1.openapi.errors import (
    UNAUTHENTICATED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    error_response,
)

ADMIN_RECIPE_LIST_ITEM_EXAMPLE = {
    "recipe_id": 101,
    "title": "집에서도 고급 한우 육회 맛있게 만드는 법",
    "summary": "고소한 양념과 배를 곁들인 한우 육회입니다.",
    "servings": 2.0,
    "cooking_time_minutes": 20,
    "kcal_per_serving": 320,
    "difficulty": "easy",
    "visibility": "PUBLIC",
    "author_type": "SOURCE",
    "source_id": 1,
    "source_site": "10000recipe",
    "source_recipe_id": "7041234",
    "source_record_id": None,
    "source_dataset_id": None,
    "source_dataset_name": None,
    "is_active": True,
    "created_at": "2026-05-17T14:20:00+09:00",
    "updated_at": "2026-05-17T14:20:00+09:00",
    "likes_count": 12,
    "scrap_count": 5,
    "has_nutrition": True,
    "has_classification": True,
    "has_embedding": True,
}

ADMIN_RECIPE_LIST_RESPONSE_EXAMPLE = {
    "items": [ADMIN_RECIPE_LIST_ITEM_EXAMPLE],
    "next_cursor": "eyJzb3J0IjoibGF0ZXN0IiwicmVjaXBlX2lkIjoxMDF9",
    "has_next": True,
}

ADMIN_RECIPE_DETAIL_EXAMPLE = {
    **ADMIN_RECIPE_LIST_ITEM_EXAMPLE,
    "description": "신선한 한우와 배, 고소한 양념으로 만드는 육회 레시피입니다.",
    "cooking_time_minutes": 20,
    "author_id": None,
    "source_author_name": "만개의레시피",
    "source_author_url": "https://www.10000recipe.com/profile/example",
    "source_url": "https://www.10000recipe.com/recipe/7041234",
    "source_organization": None,
    "source_license": None,
    "source_license_url": None,
    "source_published_at": "2026-05-13T10:00:00+09:00",
    "stats": {
        "likes_count": 12,
        "scrap_count": 5,
    },
    "ingredients": [
        {
            "ingredient_id": 1001,
            "group_name": "주재료",
            "name": "한우 우둔살",
            "normalized_name": "소고기",
            "amount_text": "200g",
            "quantity": 200.0,
            "unit": "g",
            "note": "육회용",
            "raw_text": "한우 우둔살 200g",
            "is_optional": False,
            "sort_order": 1,
        }
    ],
    "steps": [
        {
            "step_id": 2001,
            "step_no": 1,
            "instruction": "고기는 키친타월로 핏물을 제거한 뒤 먹기 좋게 썹니다.",
            "tip": "고기는 조리 직전까지 차갑게 보관합니다.",
            "sort_order": 1,
        }
    ],
    "labels": [
        {
            "label_id": 3001,
            "label_type": "CATEGORY",
            "label_value": "한식",
            "source": "RULE",
            "confidence_score": 0.9,
            "sort_order": 1,
        }
    ],
    "nutrition": {
        "kcal_per_serving": 320,
        "carbohydrate_grams": 8.0,
        "protein_grams": 28.0,
        "fat_grams": 18.0,
        "sodium_milligrams": 620.0,
        "source": "AI_ESTIMATED",
        "raw_payload": {},
        "updated_at": "2026-05-17T14:20:00+09:00",
    },
    "classification": {
        "cuisine_type": "KOREAN",
        "dish_type": "SIDE_DISH",
        "cooking_methods": ["RAW"],
        "meal_types": ["DINNER"],
        "occasions": [],
        "situations": ["GUEST"],
        "main_ingredients": ["소고기"],
        "taste_keywords": ["고소함", "짭짤함"],
        "texture_keywords": ["부드러움"],
        "diet_keywords": [],
        "allergen_keywords": [],
        "equipment": ["볼", "칼"],
        "season": [],
        "category_labels": ["한식", "고기"],
        "classification_source": "RULE",
        "confidence_score": 0.86,
        "updated_at": "2026-05-17T14:20:00+09:00",
    },
    "media": [
        {
            "media_id": 4001,
            "step_id": None,
            "media_type": "IMAGE",
            "image_role": "MAIN",
            "source_url": "https://example.com/source.jpg",
            "storage_url": "https://cdn.naengo.example/recipes/101/main.jpg",
            "thumbnail_url": "https://cdn.naengo.example/recipes/101/thumb.jpg",
            "width": 1200,
            "height": 800,
            "file_size_bytes": 245000,
            "mime_type": "image/jpeg",
            "storage_provider": "S3",
            "generation_id": None,
            "is_primary": True,
            "sort_order": 1,
            "created_at": "2026-05-17T14:20:00+09:00",
        }
    ],
}

ADMIN_RECIPE_NOT_FOUND_RESPONSE = error_response(
    "레시피를 찾을 수 없습니다.",
    "RECIPE_NOT_FOUND",
    "Recipe was not found.",
)

INVALID_CURSOR_RESPONSE = error_response(
    "커서 값이 올바르지 않습니다.",
    "INVALID_CURSOR",
    "Cursor is invalid.",
)

GET_ADMIN_RECIPES_SUMMARY = "[관리자] 정식 레시피 목록 조회"
GET_ADMIN_RECIPES_DESCRIPTION = r"""
관리자 화면에서 정식 레시피(`recipes`) 목록을 조회합니다.

목록 응답은 운영 검수에 필요한 최소 요약 정보와 상태 플래그를 반환합니다.
재료, 조리 단계, 라벨, 영양 정보, 이미지 목록까지 확인해야 하면
`GET /api/v1/admin/recipes/{recipe_id}`를 사용합니다.

**정렬**

| 값 | 설명 | 커서 기준 |
| --- | --- | --- |
| `latest` | 최신 등록순입니다. 기본값입니다. | `recipe_id` 내림차순 |
| `likes` | 좋아요가 많은 순입니다. | `likes_count`, `recipe_id` 내림차순 |
| `scraps` | 스크랩이 많은 순입니다. | `scrap_count`, `recipe_id` 내림차순 |

**필터**

- `is_active`: 서비스 노출 활성 여부입니다.
- `source_site`: 원천 사이트입니다. 예: `10000recipe`, `foodsafetykorea`
- `author_type`: 작성 주체입니다. `ADMIN`, `USER`, `SOURCE`
- `visibility`: 공개 범위입니다. `PUBLIC`, `ADMIN_ONLY`
- `difficulty`: 요리 난이도입니다. `easy`, `normal`, `hard`
- `q`: 레시피 제목에 포함된 문자열로 부분 검색합니다.

**`q` 검색어 사용법**

- 검색 대상은 현재 `recipes.title`입니다. 재료/설명/태그까지는 검색하지 않습니다.
- 대소문자를 구분하지 않는 부분 검색입니다.
- 예: `q=김치`는 `김치찌개`, `참치김치볶음밥`처럼 제목에 `김치`가 포함된 레시피를 찾습니다.
- 예: `q=육회`는 `집에서도 고급 한우 육회 맛있게 만드는 법`을 찾을 수 있습니다.
- 검색어에 공백이나 한글이 있으면 URL 인코딩해서 전달합니다.
  예: `q=한우%20육회`
- `q`를 비우거나 전달하지 않으면 제목 검색 필터를 적용하지 않습니다.

`cursor`는 이전 응답의 `next_cursor`를 그대로 전달합니다.
다른 `sort`에서 받은 커서를 섞어 쓰면 `400 INVALID_CURSOR`를 반환합니다.
"""

GET_ADMIN_RECIPES_RESPONSES = {
    200: {
        "description": "관리자용 레시피 목록",
        "content": {
            "application/json": {"example": ADMIN_RECIPE_LIST_RESPONSE_EXAMPLE}
        },
    },
    400: INVALID_CURSOR_RESPONSE,
    401: UNAUTHENTICATED_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}

GET_ADMIN_RECIPE_SUMMARY = "[관리자] 정식 레시피 상세 조회"
GET_ADMIN_RECIPE_DESCRIPTION = r"""
관리자가 정식 레시피 하나의 운영/검수 정보를 조회합니다.

상세 응답에는 목록 필드에 더해 다음 정보가 포함됩니다.

- 원천 정보: 원본 URL, 원천 작성자, 공공데이터 출처, 라이선스
- 구조화 데이터: 재료, 조리 단계, 라벨
- 품질 보조 정보: 영양 정보, 분류 정보, embedding 생성 여부
- 미디어: 대표 이미지, 썸네일, 단계 이미지, AI 생성 이미지 후보 연결 정보

사용자 앱에 그대로 노출하는 응답이 아니라 관리자 검수와 운영 도구를 위한
확장 응답입니다.
"""

GET_ADMIN_RECIPE_RESPONSES = {
    200: {
        "description": "관리자용 레시피 상세",
        "content": {
            "application/json": {"example": ADMIN_RECIPE_DETAIL_EXAMPLE}
        },
    },
    401: UNAUTHENTICATED_RESPONSE,
    404: ADMIN_RECIPE_NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}
