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

RECIPE_EXAMPLE = {
    "id": 1,
    "title": "김치두부찌개",
    "summary": "김치와 두부로 끓이는 칼칼한 찌개",
    "description": "칼칼하고 깊은 맛의 김치두부찌개입니다.",
    "ingredients": [INGREDIENT_EXAMPLE],
    "steps": [
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
    ],
    "servings": 2.0,
    "cooking_time_minutes": 20,
    "kcal_per_serving": 180,
    "difficulty": "easy",
    "category": ["한식", "찌개"],
    "tags": ["얼큰함", "국물요리"],
    "tips": ["김치는 충분히 익은 것을 사용하면 맛이 더 좋습니다."],
    "source_url": "https://www.10000recipe.com/recipe/123456",
    "main_image_url": "https://example.com/source-image.jpg",
    "author_type": "ADMIN",
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
    "content": "김치랑 두부 있는데 뭐 만들 수 있어?",
    "recipes": None,
    "created_at": "2026-04-29T12:00:00+09:00",
}

CHAT_MESSAGE_MODEL_EXAMPLE = {
    "message_id": 2,
    "role": "model",
    "content": "김치와 두부로 만들 수 있는 김치두부찌개를 추천드려요.",
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
    "source_main_image_url": "https://example.com/kimchi-jjigae.jpg",
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
            "sort_order": 1,
        }
    ],
    "labels": [{"label_type": "CATEGORY", "label_value": "찌개", "sort_order": 1}],
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

USER_RECIPE_REVIEWED_EXAMPLE = {
    **USER_RECIPE_EXAMPLE,
    "status": "APPROVED",
    "reviewed_by": 1,
    "reviewed_at": "2026-05-06T10:00:00+09:00",
    "imported_recipe_id": None,
    "imported_at": None,
}

RECIPE_DETAIL_RESPONSE_EXAMPLE = {
    **RECIPE_EXAMPLE,
    "id": 1,
    "created_at": "2026-04-01T09:00:00+09:00",
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

RECIPE_SOURCE_LIST_ITEM_EXAMPLE = {
    "source_id": 10,
    "source_site": "10000recipe",
    "source_type": "WEB_SCRAPE",
    "parser_type": "AI",
    "source_url": "https://www.10000recipe.com/recipe/123456",
    "title": "김치두부찌개",
    "parse_status": "PARSED",
    "review_status": "PENDING",
    "import_status": "NOT_IMPORTED",
    "collected_at": "2026-05-13T10:00:00+09:00",
    "has_errors": False,
}

RECIPE_SOURCE_EXTRACTION_EXAMPLE = {
    "title": "김치두부찌개",
    "summary": "김치와 두부로 끓이는 간단한 찌개",
    "description": "잘 익은 김치를 볶아 깊은 맛을 낸 찌개입니다.",
    "servings": 2.0,
    "cooking_time_minutes": 25,
    "kcal_per_serving": 320,
    "difficulty": "easy",
    "source_main_image_url": "https://example.com/source-image.jpg",
    "source_thumbnail_url": "https://example.com/source-thumb.jpg",
    "source_video_url": None,
    "content_hash": "sha256-example",
    "nutrition": {
        "serving_weight_grams": 250,
        "carbohydrate_grams": 12,
        "protein_grams": 8,
        "fat_grams": 4,
        "sodium_milligrams": 300,
        "source": "SOURCE",
        "raw": {"sodium": "300"},
    },
    "completeness_score": 0.92,
    "confidence_score": 0.88,
    "ingredients": [
        {
            "group_name": "메인",
            "name": "김치",
            "normalized_name": "김치",
            "amount_text": "200g",
            "quantity": 200,
            "unit": "g",
            "note": "잘 익은 것",
            "raw_text": "김치 200g",
            "is_optional": False,
            "sort_order": 1,
        }
    ],
    "steps": [
        {
            "step_no": 1,
            "instruction": "냄비에 김치를 볶습니다.",
            "source_image_url": None,
            "tip": None,
            "raw_text": "김치를 볶는다.",
            "sort_order": 1,
        }
    ],
    "labels": [
        {
            "label_type": "CATEGORY",
            "label_value": "찌개",
            "confidence_score": 0.9,
            "source": "RULE",
            "sort_order": 1,
        }
    ],
}

RECIPE_SOURCE_DETAIL_EXAMPLE = {
    "source_id": 10,
    "source_type": "WEB_SCRAPE",
    "source_site": "10000recipe",
    "parser_type": "AI",
    "source_recipe_id": "123456",
    "source_url": "https://www.10000recipe.com/recipe/123456",
    "source_author_name": "만개의레시피",
    "source_author_url": "https://example.com/author",
    "source_published_at": "2026-05-01T09:00:00+09:00",
    "raw_payload": {"title": "김치두부찌개"},
    "raw_content_hash": "raw-sha256-example",
    "parse_status": "PARSED",
    "review_status": "PENDING",
    "import_status": "NOT_IMPORTED",
    "validation_errors": [],
    "extraction_version": "ai-v1",
    "collected_at": "2026-05-13T10:00:00+09:00",
    "parsed_at": "2026-05-13T10:01:00+09:00",
    "reviewed_at": None,
    "imported_at": None,
    "imported_recipe_id": None,
    "extraction": RECIPE_SOURCE_EXTRACTION_EXAMPLE,
    "created_at": "2026-05-13T10:00:00+09:00",
    "updated_at": "2026-05-13T10:01:00+09:00",
}

RECIPE_SOURCE_LIST_RESPONSE_EXAMPLE = {
    "items": [RECIPE_SOURCE_LIST_ITEM_EXAMPLE],
    "next_cursor": "9",
    "has_next": True,
}

RECIPE_SOURCE_IMPORT_ACCEPTED_EXAMPLE = {
    "status": "accepted",
    "source_id": 10,
}
