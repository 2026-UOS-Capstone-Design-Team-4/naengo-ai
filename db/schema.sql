CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER'
        CHECK (role IN ('USER', 'ADMIN')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    user_input JSONB NOT NULL DEFAULT '[]',
    allergies JSONB NOT NULL DEFAULT '[]',
    dietary_restrictions JSONB NOT NULL DEFAULT '[]',
    preferred_ingredients JSONB NOT NULL DEFAULT '[]',
    disliked_ingredients JSONB NOT NULL DEFAULT '[]',
    preferred_categories JSONB NOT NULL DEFAULT '[]',
    frequently_used_ingredients JSONB NOT NULL DEFAULT '[]',
    taste_keywords JSONB NOT NULL DEFAULT '[]',
    cooking_skill VARCHAR(10)
        CHECK (cooking_skill IN ('easy', 'normal', 'hard')),
    preferred_cooking_time INTEGER,
    serving_size NUMERIC(4, 1),
    recent_recipe_ids JSONB NOT NULL DEFAULT '[]',
    ai_analyzed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recipe_sources (
    source_id SERIAL PRIMARY KEY,
    source_type VARCHAR(30) NOT NULL
        CHECK (source_type IN ('INTERNAL', 'USER_SUBMISSION', 'WEB_SCRAPE', 'VIDEO', 'EXTERNAL_API')),
    source_site VARCHAR(50) NOT NULL,
    parser_type VARCHAR(20) NOT NULL
        CHECK (parser_type IN ('MANUAL', 'HTML', 'AI', 'API')),
    source_recipe_id VARCHAR(100),
    source_url VARCHAR(1024),
    source_author_name VARCHAR(255),
    source_author_url VARCHAR(1024),
    raw_payload JSONB NOT NULL DEFAULT '{}',
    normalized_payload JSONB NOT NULL DEFAULT '{}',
    source_metadata JSONB NOT NULL DEFAULT '{}',
    normalized_metadata JSONB NOT NULL DEFAULT '{}',
    content_hash VARCHAR(64),
    status VARCHAR(30) NOT NULL DEFAULT 'COLLECTED'
        CHECK (
            status IN (
                'COLLECTED',
                'PARSED',
                'INVALID',
                'DUPLICATE',
                'READY',
                'REVIEW_REQUIRED',
                'IMPORTED',
                'REJECTED'
            )
        ),
    validation_errors JSONB NOT NULL DEFAULT '[]',
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parsed_at TIMESTAMP WITH TIME ZONE,
    imported_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_site, source_recipe_id),
    UNIQUE (source_url)
);

CREATE TABLE recipes (
    recipe_id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES recipe_sources(source_id) ON DELETE SET NULL,

    title VARCHAR(255) NOT NULL,
    summary TEXT,
    description TEXT NOT NULL,
    content TEXT,

    ingredients JSONB NOT NULL DEFAULT '[]',
    ingredients_raw TEXT NOT NULL,
    instructions JSONB NOT NULL DEFAULT '[]',

    servings NUMERIC(4, 1) NOT NULL,
    cooking_time INTEGER NOT NULL,
    calories INTEGER,
    difficulty VARCHAR(10) NOT NULL
        CHECK (difficulty IN ('easy', 'normal', 'hard')),
    difficulty_score INTEGER
        CHECK (difficulty_score BETWEEN 1 AND 5),

    category JSONB NOT NULL DEFAULT '[]',
    tags JSONB NOT NULL DEFAULT '[]',
    tips JSONB NOT NULL DEFAULT '[]',

    cuisine_type VARCHAR(50),
    dish_type VARCHAR(50),
    cooking_method VARCHAR(50),
    situation JSONB NOT NULL DEFAULT '[]',
    main_ingredients JSONB NOT NULL DEFAULT '[]',
    equipment JSONB NOT NULL DEFAULT '[]',
    meal_type JSONB NOT NULL DEFAULT '[]',
    taste_keywords JSONB NOT NULL DEFAULT '[]',
    diet_keywords JSONB NOT NULL DEFAULT '[]',

    video_url VARCHAR(1024),
    image_url VARCHAR(1024),
    thumbnail_url VARCHAR(1024),
    image_urls JSONB NOT NULL DEFAULT '[]',

    source_type VARCHAR(30)
        CHECK (source_type IN ('INTERNAL', 'USER_SUBMISSION', 'WEB_SCRAPE', 'VIDEO', 'EXTERNAL_API')),
    source_site VARCHAR(50),
    parser_type VARCHAR(20)
        CHECK (parser_type IN ('MANUAL', 'HTML', 'AI', 'API')),
    source_recipe_id VARCHAR(100),
    source_url VARCHAR(1024),
    source_author_name VARCHAR(255),
    source_author_url VARCHAR(1024),
    source_collected_at TIMESTAMP WITH TIME ZONE,
    source_published_at TIMESTAMP WITH TIME ZONE,
    source_metadata JSONB NOT NULL DEFAULT '{}',
    normalized_metadata JSONB NOT NULL DEFAULT '{}',

    is_active BOOLEAN NOT NULL DEFAULT true,
    author_type VARCHAR(20) NOT NULL DEFAULT 'ADMIN'
        CHECK (author_type IN ('ADMIN', 'USER')),
    author_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    embedding VECTOR(1536),

    UNIQUE (source_site, source_recipe_id),
    UNIQUE (source_url)
);

ALTER TABLE recipe_sources
ADD COLUMN imported_recipe_id INTEGER REFERENCES recipes(recipe_id) ON DELETE SET NULL;

CREATE TABLE recipe_ingredients (
    ingredient_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    amount VARCHAR(50),
    unit VARCHAR(50),
    group_name VARCHAR(100),
    type VARCHAR(50),
    note TEXT,
    raw_text TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE recipe_steps (
    step_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    image_url VARCHAR(1024),
    video_timestamp VARCHAR(20),
    source_metadata JSONB NOT NULL DEFAULT '{}',
    UNIQUE (recipe_id, step_no)
);

CREATE TABLE recipe_image_generations (
    generation_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    requested_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    source_id INTEGER REFERENCES recipe_sources(source_id) ON DELETE SET NULL,
    purpose VARCHAR(30) NOT NULL DEFAULT 'MAIN_IMAGE'
        CHECK (purpose IN ('MAIN_IMAGE', 'THUMBNAIL')),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    image_url VARCHAR(1024),
    thumbnail_url VARCHAR(1024),
    status VARCHAR(30) NOT NULL DEFAULT 'REQUESTED'
        CHECK (status IN ('REQUESTED', 'GENERATING', 'SUCCEEDED', 'FAILED', 'SELECTED', 'REJECTED')),
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    selected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pending_recipes (
    pending_recipe_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    ingredients JSONB,
    ingredients_raw TEXT,
    instructions JSONB,
    servings NUMERIC(4, 1),
    cooking_time INTEGER,
    calories INTEGER,
    difficulty VARCHAR(10)
        CHECK (difficulty IN ('easy', 'normal', 'hard')),
    category JSONB,
    tags JSONB,
    tips JSONB,
    video_url VARCHAR(1024),
    image_url VARCHAR(1024),
    is_active BOOLEAN NOT NULL DEFAULT true,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    admin_note TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_rooms (
    room_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(100) DEFAULT '새로운 레시피 상담',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    message_id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES chat_rooms(room_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'model')),
    content TEXT NOT NULL,
    recipe_ids JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE likes (
    like_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, recipe_id)
);

CREATE TABLE scraps (
    scrap_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, recipe_id)
);

CREATE TABLE recipe_stats (
    recipe_id INTEGER PRIMARY KEY REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    likes_count INTEGER NOT NULL DEFAULT 0 CHECK (likes_count >= 0),
    scrap_count INTEGER NOT NULL DEFAULT 0 CHECK (scrap_count >= 0)
);

CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER touch_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER touch_user_profiles_updated_at
BEFORE UPDATE ON user_profiles
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER touch_recipe_sources_updated_at
BEFORE UPDATE ON recipe_sources
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER touch_recipes_updated_at
BEFORE UPDATE ON recipes
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER touch_recipe_image_generations_updated_at
BEFORE UPDATE ON recipe_image_generations
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER touch_pending_recipes_updated_at
BEFORE UPDATE ON pending_recipes
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER touch_chat_rooms_updated_at
BEFORE UPDATE ON chat_rooms
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE OR REPLACE FUNCTION create_recipe_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO recipe_stats (recipe_id)
    VALUES (NEW.recipe_id)
    ON CONFLICT (recipe_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_recipe_stats
AFTER INSERT ON recipes
FOR EACH ROW EXECUTE FUNCTION create_recipe_stats();

CREATE OR REPLACE FUNCTION update_likes_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO recipe_stats (recipe_id, likes_count, scrap_count)
        VALUES (NEW.recipe_id, 1, 0)
        ON CONFLICT (recipe_id)
        DO UPDATE SET likes_count = recipe_stats.likes_count + 1;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE recipe_stats
        SET likes_count = GREATEST(likes_count - 1, 0)
        WHERE recipe_id = OLD.recipe_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_likes_count
AFTER INSERT OR DELETE ON likes
FOR EACH ROW EXECUTE FUNCTION update_likes_count();

CREATE OR REPLACE FUNCTION update_scrap_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO recipe_stats (recipe_id, likes_count, scrap_count)
        VALUES (NEW.recipe_id, 0, 1)
        ON CONFLICT (recipe_id)
        DO UPDATE SET scrap_count = recipe_stats.scrap_count + 1;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE recipe_stats
        SET scrap_count = GREATEST(scrap_count - 1, 0)
        WHERE recipe_id = OLD.recipe_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_scrap_count
AFTER INSERT OR DELETE ON scraps
FOR EACH ROW EXECUTE FUNCTION update_scrap_count();

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_nickname ON users(nickname);

CREATE INDEX idx_recipe_sources_status ON recipe_sources(status);
CREATE INDEX idx_recipe_sources_source ON recipe_sources(source_site, source_recipe_id);
CREATE INDEX idx_recipe_sources_content_hash ON recipe_sources(content_hash);
CREATE INDEX idx_recipe_sources_metadata_gin ON recipe_sources USING GIN (normalized_metadata);

CREATE INDEX idx_recipes_active_id ON recipes(is_active, recipe_id DESC);
CREATE INDEX idx_recipes_source ON recipes(source_site, source_recipe_id);
CREATE INDEX idx_recipes_source_url ON recipes(source_url);
CREATE INDEX idx_recipes_cuisine_type ON recipes(cuisine_type);
CREATE INDEX idx_recipes_dish_type ON recipes(dish_type);
CREATE INDEX idx_recipes_cooking_method ON recipes(cooking_method);
CREATE INDEX idx_recipes_category_gin ON recipes USING GIN (category);
CREATE INDEX idx_recipes_tags_gin ON recipes USING GIN (tags);
CREATE INDEX idx_recipes_main_ingredients_gin ON recipes USING GIN (main_ingredients);
CREATE INDEX idx_recipes_normalized_metadata_gin ON recipes USING GIN (normalized_metadata);
CREATE INDEX idx_recipes_embedding ON recipes USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_name ON recipe_ingredients(name);
CREATE INDEX idx_recipe_steps_recipe_id ON recipe_steps(recipe_id);
CREATE INDEX idx_recipe_image_generations_recipe_status
ON recipe_image_generations(recipe_id, status, created_at DESC);

CREATE INDEX idx_chat_rooms_user_active_updated ON chat_rooms(user_id, is_active, updated_at DESC);
CREATE INDEX idx_chat_messages_room_created ON chat_messages(room_id, created_at);
CREATE INDEX idx_pending_recipes_user_status_created ON pending_recipes(user_id, status, created_at DESC);
CREATE INDEX idx_likes_recipe_id ON likes(recipe_id);
CREATE INDEX idx_scraps_recipe_id ON scraps(recipe_id);
CREATE INDEX idx_scraps_user_created ON scraps(user_id, scrap_id DESC);
