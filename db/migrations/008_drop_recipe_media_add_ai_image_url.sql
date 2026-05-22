ALTER TABLE recipes ADD COLUMN ai_main_image_url VARCHAR(1024);
ALTER TABLE recipe_steps ADD COLUMN ai_image_url VARCHAR(1024);

DROP TABLE IF EXISTS recipe_image_generations CASCADE;
DROP TABLE IF EXISTS recipe_media CASCADE;
