CREATE TABLE recipe_source_extracted_nutrition (
    extraction_id INTEGER PRIMARY KEY
        REFERENCES recipe_source_extractions(extraction_id) ON DELETE CASCADE,
    serving_weight_grams NUMERIC(10, 2),
    carbohydrate_grams NUMERIC(10, 2),
    protein_grams NUMERIC(10, 2),
    fat_grams NUMERIC(10, 2),
    sodium_milligrams NUMERIC(10, 2),
    source VARCHAR(30) NOT NULL DEFAULT 'SOURCE'
        CHECK (source IN ('SOURCE', 'RULE', 'AI', 'ADMIN')),
    raw JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO recipe_source_extracted_nutrition (
    extraction_id,
    serving_weight_grams,
    carbohydrate_grams,
    protein_grams,
    fat_grams,
    sodium_milligrams,
    source,
    raw
)
SELECT
    extraction_id,
    serving_weight_grams,
    carbohydrate_grams,
    protein_grams,
    fat_grams,
    sodium_milligrams,
    COALESCE(nutrition_source, 'SOURCE'),
    COALESCE(nutrition_raw, '{}'::jsonb)
FROM recipe_source_extractions
WHERE serving_weight_grams IS NOT NULL
   OR carbohydrate_grams IS NOT NULL
   OR protein_grams IS NOT NULL
   OR fat_grams IS NOT NULL
   OR sodium_milligrams IS NOT NULL
   OR nutrition_source IS NOT NULL
   OR nutrition_raw <> '{}'::jsonb;

ALTER TABLE recipe_source_extractions
DROP COLUMN serving_weight_grams,
DROP COLUMN carbohydrate_grams,
DROP COLUMN protein_grams,
DROP COLUMN fat_grams,
DROP COLUMN sodium_milligrams,
DROP COLUMN nutrition_source,
DROP COLUMN nutrition_raw;

CREATE TRIGGER touch_recipe_source_extracted_nutrition_updated_at
BEFORE UPDATE ON recipe_source_extracted_nutrition
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
