INGREDIENT_EXAMPLE = {
    "name": "김치",
    "amount": "200",
    "unit": "g",
    "type": "메인",
    "note": "잘 익은 것",
}

RECIPE_EXAMPLE = {
    "id": 1,
    "title": "김치두부찌개",
    "description": "칼칼하고 깊은 맛의 김치두부찌개입니다.",
    "ingredients": [INGREDIENT_EXAMPLE],
    "ingredients_raw": "김치 200g, 두부 1모, 돼지고기 100g",
    "steps": [
        {"step_no": 1, "instruction": "냄비에 기름을 두르고 돼지고기를 볶습니다.", "tip": None},
        {"step_no": 2, "instruction": "김치를 넣고 함께 볶습니다.", "tip": None},
        {"step_no": 3, "instruction": "물을 붓고 끓어오르면 두부를 넣습니다.", "tip": None},
        {"step_no": 4, "instruction": "간을 맞추고 5분 더 끓입니다.", "tip": "기호에 따라 고추가루를 추가해도 좋습니다."},
    ],
    "servings": 2.0,
    "cooking_time_minutes": 20,
    "kcal_per_serving": 180,
    "difficulty": "easy",
    "category": ["한식", "찌개"],
    "tags": ["얼큰함", "국물요리"],
    "tips": ["김치는 충분히 익은 것을 사용하면 맛이 더 좋습니다."],
    "video_url": "https://youtube.com/watch?v=example",
    "image_url": "https://example.com/image.jpg",
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
    "email": "user@naengo.com",
    "nickname": "냉장고요리왕",
    "role": "USER",
    "is_active": True,
    "is_blocked": False,
    "created_at": "2026-04-01T09:00:00+09:00",
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
    "submission_text": (
        "묵은지를 쓰면 훨씬 맛있어요. 돼지고기는 앞다리살이 잘 어울리고 "
        "김치는 충분히 볶아야 깊은 맛이 납니다."
    ),
    "draft_payload": {
        "description": "집에서 자주 해먹는 진한 김치찌개",
        "ingredients": [
            {
                "name": "묵은지",
                "amount": "300",
                "unit": "g",
                "type": "메인",
                "note": "충분히 익은 것",
            },
            {
                "name": "돼지고기 앞다리살",
                "amount": "200",
                "unit": "g",
                "type": "메인",
                "note": None,
            },
            {"name": "두부", "amount": "1", "unit": "모", "type": "부재료", "note": None},
            {"name": "대파", "amount": "1", "unit": "대", "type": "부재료", "note": None},
        ],
        "ingredients_raw": "묵은지 300g, 돼지고기 앞다리살 200g, 두부 1모, 대파 1대",
        "instructions": [
            "돼지고기를 먹기 좋은 크기로 썹니다.",
            "냄비에 기름을 두르고 돼지고기와 김치를 함께 볶습니다.",
            "물 500ml를 붓고 센 불에서 끓입니다.",
            "끓어오르면 두부와 대파를 넣고 중불로 10분 더 끓입니다.",
            "간을 맞추고 마무리합니다.",
        ],
        "servings": 2.0,
        "cooking_time_minutes": 25,
        "kcal_per_serving": 320,
        "difficulty": "easy",
        "category": ["한식", "찌개"],
        "tags": ["얼큰함", "국물요리", "밥도둑"],
        "tips": [
            "김치는 묵은지를 써야 깊은 맛이 납니다.",
            "돼지고기는 앞다리살이나 목살이 잘 어울립니다.",
        ],
        "video_url": "https://youtube.com/watch?v=example",
        "image_url": "https://example.com/kimchi-jjigae.jpg",
    },
    "ai_suggested_patch": {
        "description": None,
        "ingredients": [],
        "ingredients_raw": [],
        "instructions": [],
        "servings": None,
        "cooking_time_minutes": None,
        "kcal_per_serving": None,
        "difficulty": None,
        "category": [],
        "tags": [],
        "tips": [],
        "video_url": None,
        "image_url": None,
    },
    "validation_errors": [],
    "status": "PENDING",
    "import_status": "NOT_IMPORTED",
    "is_active": True,
    "admin_note": None,
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
    "admin_note": "재료 구성과 조리 순서가 명확합니다. 승인합니다.",
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
            **RECIPE_EXAMPLE,
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
