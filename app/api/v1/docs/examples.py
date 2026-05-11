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
    "instructions": [
        "냄비에 기름을 두르고 돼지고기를 볶습니다.",
        "김치를 넣고 함께 볶습니다.",
        "물을 붓고 끓어오르면 두부를 넣습니다.",
        "간을 맞추고 5분 더 끓입니다.",
    ],
    "servings": 2.0,
    "cooking_time": 20,
    "calories": 180,
    "difficulty": "easy",
    "category": ["한식", "찌개"],
    "tags": ["얼큰한", "국물요리"],
    "tips": ["김치는 충분히 익은 것을 사용해야 맛이 좋습니다."],
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
        "매운 음식을 좋아해요",
        "간단한 요리 위주로 추천해줘",
    ],
}

PENDING_RECIPE_EXAMPLE = {
    "pending_recipe_id": 1,
    "title": "엄마한테 배운 김치찌개",
    "content": (
        "묵은지를 쓰면 훨씬 맛있어요. 돼지고기는 앞다리살을 쓰고 "
        "김치는 충분히 볶아야 칼칼한 맛이 납니다."
    ),
    "description": "집에서 해먹는 진짜 김치찌개",
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
    "cooking_time": 25,
    "calories": 320,
    "difficulty": "easy",
    "category": ["한식", "찌개"],
    "tags": ["얼큰한", "국물요리", "밥도둑"],
    "tips": [
        "김치는 묵은지를 써야 깊은 맛이 납니다.",
        "돼지고기는 앞다리살이 잘 어울립니다.",
    ],
    "video_url": "https://youtube.com/watch?v=example",
    "image_url": "https://example.com/kimchi-jjigae.jpg",
    "status": "PENDING",
    "admin_note": None,
    "reviewed_at": None,
    "created_at": "2026-05-04T12:00:00+09:00",
}

PENDING_RECIPE_REVIEWED_EXAMPLE = {
    **PENDING_RECIPE_EXAMPLE,
    "status": "APPROVED",
    "admin_note": "재료 구성과 조리 순서가 명확합니다. 승인합니다.",
    "reviewed_at": "2026-05-06T10:00:00+09:00",
}

RECIPE_LIST_RESPONSE_EXAMPLE = {
    "items": [
        {
            **RECIPE_EXAMPLE,
            "created_at": "2026-04-01T09:00:00+09:00",
            "likes_count": 42,
            "scrap_count": 15,
        }
    ],
    "next_cursor": "42_1",
    "has_next": True,
}
