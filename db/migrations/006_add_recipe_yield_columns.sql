ALTER TABLE recipe_source_extractions
ADD COLUMN yield_quantity NUMERIC(10, 2),
ADD COLUMN yield_unit VARCHAR(50);

ALTER TABLE recipes
ADD COLUMN yield_quantity NUMERIC(10, 2),
ADD COLUMN yield_unit VARCHAR(50);
