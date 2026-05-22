ALTER TABLE user_recipes
RENAME COLUMN source_main_image_url TO main_image_url;

ALTER TABLE user_recipes_steps
RENAME COLUMN sourceimage_url TO image_url;
