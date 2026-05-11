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
