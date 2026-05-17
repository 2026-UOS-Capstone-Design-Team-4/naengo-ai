INSERT INTO users (
    user_id,
    email,
    password_hash,
    nickname,
    role,
    is_active,
    is_blocked
) VALUES
    (
        1,
        'admin@naengo.local',
        'local-dev-password-hash',
        'naengo_admin',
        'ADMIN',
        true,
        false
    ),
    (
        2,
        'user@naengo.local',
        'local-dev-password-hash',
        'naengo_user',
        'USER',
        true,
        false
    ),
    (
        3,
        'tester@naengo.local',
        'local-dev-password-hash',
        'naengo_tester',
        'USER',
        true,
        false
    )
ON CONFLICT (user_id) DO UPDATE SET
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    nickname = EXCLUDED.nickname,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    is_blocked = EXCLUDED.is_blocked;

SELECT setval(
    pg_get_serial_sequence('users', 'user_id'),
    GREATEST((SELECT max(user_id) FROM users), 1)
);

INSERT INTO user_profiles (
    user_id,
    user_input,
    allergies,
    dietary_restrictions,
    preferred_ingredients,
    disliked_ingredients,
    preferred_categories,
    frequently_used_ingredients,
    taste_keywords,
    cooking_skill,
    preferred_cooking_time_minutes,
    serving_size,
    recent_recipe_ids
) VALUES
    (
        1,
        '["운영자 테스트 계정"]',
        '[]',
        '[]',
        '[]',
        '[]',
        '[]',
        '[]',
        '[]',
        'normal',
        null,
        null,
        '[]'
    ),
    (
        2,
        '["평일 저녁에 빠르게 만들 수 있는 요리를 선호함"]',
        '["새우"]',
        '[]',
        '["두부", "계란", "김치"]',
        '["고수"]',
        '["한식", "반찬"]',
        '["두부", "양파", "대파"]',
        '["담백함", "칼칼함"]',
        'easy',
        20,
        2,
        '[]'
    ),
    (
        3,
        '["자취생 기준의 간단한 요리를 자주 찾음"]',
        '[]',
        '["저나트륨"]',
        '["닭가슴살", "버섯", "양배추"]',
        '["가지"]',
        '["덮밥", "샐러드"]',
        '["계란", "양배추", "버섯"]',
        '["고소함", "매콤함"]',
        'normal',
        30,
        1,
        '[]'
    )
ON CONFLICT (user_id) DO UPDATE SET
    user_input = EXCLUDED.user_input,
    allergies = EXCLUDED.allergies,
    dietary_restrictions = EXCLUDED.dietary_restrictions,
    preferred_ingredients = EXCLUDED.preferred_ingredients,
    disliked_ingredients = EXCLUDED.disliked_ingredients,
    preferred_categories = EXCLUDED.preferred_categories,
    frequently_used_ingredients = EXCLUDED.frequently_used_ingredients,
    taste_keywords = EXCLUDED.taste_keywords,
    cooking_skill = EXCLUDED.cooking_skill,
    preferred_cooking_time_minutes = EXCLUDED.preferred_cooking_time_minutes,
    serving_size = EXCLUDED.serving_size,
    recent_recipe_ids = EXCLUDED.recent_recipe_ids;
