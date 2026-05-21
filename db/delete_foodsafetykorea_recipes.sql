-- Delete production recipes imported from foodsafetykorea and reset their sources.
--
-- Preview before running:
-- SELECT COUNT(*) AS foodsafetykorea_recipe_count
-- FROM recipes r
-- JOIN recipe_sources s ON s.source_id = r.source_id
-- WHERE s.source_site = 'foodsafetykorea';

BEGIN;

WITH target_sources AS (
    SELECT DISTINCT s.source_id
    FROM recipe_sources s
    JOIN recipes r ON r.source_id = s.source_id
    WHERE s.source_site = 'foodsafetykorea'
),
deleted_recipes AS (
    DELETE FROM recipes r
    USING target_sources ts
    WHERE r.source_id = ts.source_id
    RETURNING r.recipe_id, r.source_id, r.title
),
reset_sources AS (
    UPDATE recipe_sources s
    SET
        import_status = 'NOT_IMPORTED',
        imported_recipe_id = NULL,
        imported_at = NULL,
        updated_at = CURRENT_TIMESTAMP
    WHERE s.source_id IN (SELECT source_id FROM target_sources)
    RETURNING s.source_id, s.source_site, s.import_status
)
SELECT
    (SELECT COUNT(*) FROM deleted_recipes) AS deleted_recipe_count,
    (SELECT COUNT(*) FROM reset_sources) AS reset_source_count;

COMMIT;
