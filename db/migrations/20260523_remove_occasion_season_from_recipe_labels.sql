-- recipe_labels.label_type CHECK 제약에서 OCCASION, SEASON 제거
-- 실행 전: OCCASION, SEASON 값을 가진 기존 데이터가 없는지 확인할 것
-- SELECT COUNT(*) FROM recipe_labels WHERE label_type IN ('OCCASION', 'SEASON');

DO $$
DECLARE
    v_constraint text;
BEGIN
    SELECT conname INTO v_constraint
    FROM pg_constraint
    WHERE conrelid = 'recipe_labels'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%label_type%';

    IF v_constraint IS NOT NULL THEN
        EXECUTE 'ALTER TABLE recipe_labels DROP CONSTRAINT ' || quote_ident(v_constraint);
    END IF;
END $$;

ALTER TABLE recipe_labels
    ADD CONSTRAINT recipe_labels_label_type_check
    CHECK (label_type IN ('TAG', 'TIP', 'CATEGORY', 'WARNING'));
