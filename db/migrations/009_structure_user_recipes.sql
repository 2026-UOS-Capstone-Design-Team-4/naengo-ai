ALTER TABLE user_recipes
DROP COLUMN draft_payload,
DROP COLUMN ai_suggested_patch,
ADD COLUMN description TEXT,
ADD COLUMN servings NUMERIC(4, 1),
ADD COLUMN yield_quantity NUMERIC(10, 2),
ADD COLUMN yield_unit VARCHAR(50),
ADD COLUMN cooking_time_minutes INTEGER,
ADD COLUMN kcal_per_serving INTEGER,
ADD COLUMN difficulty VARCHAR(10)
    CHECK (difficulty IN ('easy', 'normal', 'hard')),
ADD COLUMN video_url VARCHAR(1024),
ADD COLUMN source_main_image_url VARCHAR(1024);

CREATE TABLE user_recipe_ingredients (
    user_recipe_ingredient_id SERIAL PRIMARY KEY,
    user_recipe_id INTEGER NOT NULL
        REFERENCES user_recipes(user_recipe_id) ON DELETE CASCADE,
    group_name VARCHAR(100),
    name VARCHAR(100) NOT NULL,
    normalized_name VARCHAR(100),
    amount_text VARCHAR(100),
    quantity NUMERIC(10, 3),
    unit VARCHAR(50),
    note TEXT,
    raw_text TEXT,
    is_optional BOOLEAN NOT NULL DEFAULT false,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE user_recipe_steps (
    user_recipe_step_id SERIAL PRIMARY KEY,
    user_recipe_id INTEGER NOT NULL
        REFERENCES user_recipes(user_recipe_id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    source_image_url VARCHAR(1024),
    tip TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_recipe_id, step_no)
);

CREATE TABLE user_recipe_labels (
    user_recipe_label_id SERIAL PRIMARY KEY,
    user_recipe_id INTEGER NOT NULL
        REFERENCES user_recipes(user_recipe_id) ON DELETE CASCADE,
    label_type VARCHAR(30) NOT NULL
        CHECK (label_type IN ('TAG', 'TIP', 'CATEGORY', 'WARNING')),
    label_value TEXT NOT NULL,
    confidence_score NUMERIC(5, 2),
    source VARCHAR(30) NOT NULL DEFAULT 'ADMIN'
        CHECK (source IN ('USER', 'AI', 'ADMIN')),
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE user_recipe_nutrition (
    user_recipe_id INTEGER PRIMARY KEY
        REFERENCES user_recipes(user_recipe_id) ON DELETE CASCADE,
    serving_weight_grams NUMERIC(10, 2),
    carbohydrate_grams NUMERIC(10, 2),
    protein_grams NUMERIC(10, 2),
    fat_grams NUMERIC(10, 2),
    sodium_milligrams NUMERIC(10, 2),
    source VARCHAR(30) NOT NULL DEFAULT 'ADMIN'
        CHECK (source IN ('USER', 'AI', 'ADMIN')),
    raw JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER touch_user_recipe_nutrition_updated_at
BEFORE UPDATE ON user_recipe_nutrition
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
