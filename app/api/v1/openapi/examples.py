INGREDIENT_EXAMPLE = {
    "group_name": "메인",
    "name": "김치",
    "amount_text": "200g",
    "quantity": 200,
    "unit": "g",
    "note": "잘 익은 것",
    "raw_text": "김치 200g",
    "is_optional": False,
}

_RECIPE_STEPS_EXAMPLE = [
    {
        "step_no": 1,
        "instruction": "냄비에 기름을 두르고 돼지고기를 볶습니다.",
        "image_url": None,
        "tip": None,
    },
    {
        "step_no": 2,
        "instruction": "김치를 넣고 함께 볶습니다.",
        "image_url": None,
        "tip": None,
    },
    {
        "step_no": 3,
        "instruction": "물을 붓고 끓어오르면 두부를 넣습니다.",
        "image_url": None,
        "tip": None,
    },
    {
        "step_no": 4,
        "instruction": "간을 맞추고 5분 더 끓입니다.",
        "image_url": None,
        "tip": "기호에 따라 고추가루를 추가해도 좋습니다.",
    },
]

# RecipeDetailResponse(= RecipeResponse) 필드 순서 기준
RECIPE_EXAMPLE = {
    "id": 1,
    "title": "김치두부찌개",
    "summary": "김치와 두부로 끓이는 칼칼한 찌개",
    "description": "칼칼하고 깊은 맛의 김치두부찌개입니다.",
    "servings": 2.0,
    "cooking_time_minutes": 20,
    "kcal_per_serving": 180,
    "difficulty": "easy",
    "author_type": "ADMIN",
    "main_image_url": "https://example.com/source-image.jpg",
    "source_url": "https://www.10000recipe.com/recipe/123456",
    "created_at": "2026-04-01T09:00:00+09:00",
    "category": ["한식", "찌개"],
    "tags": ["얼큰함", "국물요리"],
    "tips": ["김치는 충분히 익은 것을 사용하면 맛이 더 좋습니다."],
    "warnings": [],
    "ingredients": [INGREDIENT_EXAMPLE],
    "steps": _RECIPE_STEPS_EXAMPLE,
    "likes_count": 42,
    "scrap_count": 15,
    "is_liked": False,
    "is_scrapped": False,
}

CHAT_ROOM_EXAMPLE = {
    "room_id": 1,
    "title": "김치랑 두부 있는데 뭐 만들 수 있어?",
    "created_at": "2026-04-29T12:00:00+09:00",
    "updated_at": "2026-04-29T12:05:00+09:00",
}

CHAT_MESSAGE_USER_EXAMPLE = {
    "message_id": 1,
    "role": "user",
    "content": "냉장고 사진이에요. 어떤 요리를 만들 수 있을까요?",
    "image_url": "https://example.com/chat/1/fridge.jpg",
    "recipes": None,
    "created_at": "2026-04-29T12:00:00+09:00",
}

CHAT_MESSAGE_MODEL_EXAMPLE = {
    "message_id": 2,
    "role": "model",
    "content": "김치와 두부로 만들 수 있는 김치두부찌개를 추천드려요.",
    "image_url": None,
    "recipes": [RECIPE_EXAMPLE],
    "created_at": "2026-04-29T12:00:05+09:00",
}

USER_EXAMPLE = {
    "user_id": 1,
    "username": "naengo_user_123",
    "nickname": "냉장고요리왕",
    "role": "USER",
    "is_active": True,
    "is_blocked": False,
    "user_identities": [
        {
            "id": 1,
            "provider": "KAKAO",
            "email": "user@example.com",
            "created_at": "2026-04-01T09:00:00+09:00",
        },
        {
            "id": 2,
            "provider": "GOOGLE",
            "email": "user@gmail.com",
            "created_at": "2026-05-01T09:00:00+09:00",
        },
    ],
    "created_at": "2026-04-01T09:00:00+09:00",
    "updated_at": "2026-05-22T10:30:00+09:00",
}

USER_PROFILE_EXAMPLE = {
    "user_input": [
        "새우 알레르기가 있어요",
        "매운 한식을 좋아해요",
        "간단한 요리 위주로 추천해주세요",
    ],
}

USER_RECIPE_EXAMPLE = {
    "user_recipe_id": 1,
    "user_id": 7,
    "title": "엄마한테 배운 김치찌개",
    "description": "집에서 자주 해먹는 진한 김치찌개",
    "servings": 2.0,
    "yield_quantity": None,
    "yield_unit": None,
    "cooking_time_minutes": 25,
    "kcal_per_serving": 320,
    "difficulty": "easy",
    "source_url": "https://youtube.com/watch?v=example",
    "main_image_url": "https://example.com/kimchi-jjigae.jpg",
    "category": ["찌개"],
    "tags": ["한식", "얼큰함"],
    "tips": ["묵은지를 쓰면 깊은 맛이 납니다."],
    "warnings": [],
    "ingredients": [
        {
            "name": "묵은지",
            "amount_text": "300g",
            "unit": "g",
            "group_name": "메인",
            "note": "충분히 익은 것",
            "sort_order": 1,
        }
    ],
    "steps": [
        {
            "step_no": 1,
            "instruction": "돼지고기를 먹기 좋은 크기로 썹니다.",
            "image_url": "https://example.com/kimchi-step-1.jpg",
            "sort_order": 1,
        }
    ],
    "nutrition": None,
    "status": "PENDING",
    "import_status": "NOT_IMPORTED",
    "is_active": True,
    "rejection_reason": None,
    "reviewed_by": None,
    "reviewed_at": None,
    "imported_recipe_id": None,
    "imported_at": None,
    "created_at": "2026-05-04T12:00:00+09:00",
    "updated_at": "2026-05-04T12:00:00+09:00",
}

USER_RECIPE_LIST_ITEM_EXAMPLE = {
    "user_recipe_id": 1,
    "user_id": 7,
    "title": "엄마한테 배운 김치찌개",
    "description": "집에서 자주 해먹는 진한 김치찌개",
    "servings": 2.0,
    "yield_quantity": None,
    "yield_unit": None,
    "cooking_time_minutes": 25,
    "kcal_per_serving": 320,
    "difficulty": "easy",
    "main_image_url": "https://example.com/kimchi-jjigae.jpg",
    "category": ["찌개"],
    "tags": ["한식", "얼큰함"],
    "status": "PENDING",
    "import_status": "NOT_IMPORTED",
    "is_active": True,
    "rejection_reason": None,
    "created_at": "2026-05-04T12:00:00+09:00",
    "updated_at": "2026-05-04T12:00:00+09:00",
}

USER_RECIPE_AUTHOR_EXAMPLE = {
    "user_id": 7,
    "nickname": "냉장고요리왕",
}

USER_RECIPE_PUBLIC_EXAMPLE = {
    **USER_RECIPE_EXAMPLE,
    "status": "APPROVED",
    "user": USER_RECIPE_AUTHOR_EXAMPLE,
}

USER_RECIPE_PUBLIC_LIST_ITEM_EXAMPLE = {
    **USER_RECIPE_LIST_ITEM_EXAMPLE,
    "status": "APPROVED",
    "user": USER_RECIPE_AUTHOR_EXAMPLE,
}

USER_RECIPE_PUBLIC_LIST_RESPONSE_EXAMPLE = {
    "items": [USER_RECIPE_PUBLIC_LIST_ITEM_EXAMPLE],
    "next_cursor": (
        "eyJzb3J0IjoiYXBwcm92ZWRfbGF0ZXN0IiwiY3JlYXRlZF9hdCI6IjIwMjYtMDUt"
        "MDRUMTI6MDA6MDArMDk6MDAiLCJ1c2VyX3JlY2lwZV9pZCI6MX0"
    ),
    "has_next": True,
}

USER_RECIPE_REPORT_EXAMPLE = {
    "report_id": 1,
    "user_recipe_id": 22,
    "reporter_user_id": 7,
    "recipe_owner_user_id": 8,
    "reason": "INAPPROPRIATE",
    "description": "부적절한 표현이 포함되어 있어요",
    "status": "PENDING",
    "review_note": None,
    "reviewed_by": None,
    "reviewed_at": None,
    "created_at": "2026-05-25T12:00:00+09:00",
    "updated_at": "2026-05-25T12:00:00+09:00",
}

USER_RECIPE_REPORT_LIST_RESPONSE_EXAMPLE = {
    "items": [USER_RECIPE_REPORT_EXAMPLE],
    "next_cursor": "eyJzb3J0IjoibGF0ZXN0IiwicmVwb3J0X2lkIjoxfQ",
    "has_next": True,
}

USER_RECIPE_REVIEWED_EXAMPLE = {
    **USER_RECIPE_EXAMPLE,
    "status": "APPROVED",
    "reviewed_by": 1,
    "reviewed_at": "2026-05-06T10:00:00+09:00",
    "imported_recipe_id": None,
    "imported_at": None,
}

RECIPE_DETAIL_RESPONSE_EXAMPLE = {
    "id": 1,
    "title": "김치두부찌개",
    "summary": "김치와 두부로 끓이는 칼칼한 찌개",
    "description": "칼칼하고 깊은 맛의 김치두부찌개입니다.",
    "servings": 2.0,
    "cooking_time_minutes": 20,
    "kcal_per_serving": 180,
    "difficulty": "easy",
    "author_type": "ADMIN",
    "main_image_url": "https://example.com/source-image.jpg",
    "source_url": "https://www.10000recipe.com/recipe/123456",
    "created_at": "2026-04-01T09:00:00+09:00",
    "category": ["한식", "찌개"],
    "tags": ["얼큰함", "국물요리"],
    "tips": ["김치는 충분히 익은 것을 사용하면 맛이 더 좋습니다."],
    "warnings": [],
    "ingredients": [INGREDIENT_EXAMPLE],
    "steps": _RECIPE_STEPS_EXAMPLE,
    "likes_count": 42,
    "scrap_count": 15,
    "is_liked": True,
    "is_scrapped": False,
}

RECIPE_STATS_RESPONSE_EXAMPLE = {
    "likes_count": 43,
    "scrap_count": 15,
}

RECIPE_LIST_RESPONSE_EXAMPLE = {
    "items": [
        {
            "id": 1,
            "title": "김치두부찌개",
            "summary": "김치와 두부로 끓이는 칼칼한 찌개",
            "servings": 2.0,
            "cooking_time_minutes": 20,
            "kcal_per_serving": 180,
            "difficulty": "easy",
            "main_image_url": "https://example.com/source-image.jpg",
            "category": ["한식", "찌개"],
            "tags": ["얼큰함", "국물요리"],
            "created_at": "2026-04-01T09:00:00+09:00",
            "likes_count": 42,
            "scrap_count": 15,
            "is_liked": True,
            "is_scrapped": False,
        }
    ],
    "next_cursor": "eyJzb3J0IjoibGF0ZXN0IiwicmVjaXBlX2lkIjoxfQ",
    "has_next": True,
}


RECIPE_RESPONSE_TABLE = r"""
**RecipeResponse 구조**

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | int | 레시피 ID |
| `title` | string | 레시피 제목 |
| `summary` | string \| null | 레시피 요약 |
| `description` | string | 레시피 설명 |
| `servings` | float | 인분 수 |
| `cooking_time_minutes` | int | 조리 시간(분) |
| `kcal_per_serving` | int \| null | 1인분당 kcal |
| `difficulty` | string | 난이도(`easy` / `normal` / `hard`) |
| `author_type` | string | 작성자 유형(`ADMIN` / `USER` / `SOURCE`) |
| `main_image_url` | string \| null | 대표 이미지 URL |
| `source_url` | string \| null | 원본 레시피 URL |
| `created_at` | string \| null | 생성 시각 |
| `category` | string[] | 카테고리 |
| `tags` | string[] | 태그 |
| `tips` | string[] | 조리 팁 |
| `warnings` | string[] | 주의사항 |
| `ingredients` | IngredientItem[] | 재료 목록 |
| `steps` | RecipeStepResponse[] | 조리 단계 목록 |
| `likes_count` | int | 좋아요 수 |
| `scrap_count` | int | 스크랩 수 |
| `is_liked` | bool | 좋아요 여부 |
| `is_scrapped` | bool | 스크랩 여부 |
"""
