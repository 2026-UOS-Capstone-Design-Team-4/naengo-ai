-- 사용자 레시피 신고 테이블 추가
-- 신고는 레시피 노출 상태와 분리해 관리자 검토 큐로 저장한다.

CREATE TABLE IF NOT EXISTS user_recipe_reports (
    report_id SERIAL PRIMARY KEY,
    user_recipe_id INTEGER NOT NULL
        REFERENCES user_recipes(user_recipe_id) ON DELETE CASCADE,
    reporter_user_id INTEGER NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    recipe_owner_user_id INTEGER NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    reason VARCHAR(30) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    review_note TEXT,
    reviewed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_recipe_reports_recipe_reporter
        UNIQUE (user_recipe_id, reporter_user_id),
    CONSTRAINT ck_user_recipe_reports_reason
        CHECK (
            reason IN (
                'INAPPROPRIATE',
                'COPYRIGHT',
                'SPAM',
                'DANGEROUS',
                'FALSE_INFO',
                'OTHER'
            )
        ),
    CONSTRAINT ck_user_recipe_reports_status
        CHECK (status IN ('PENDING', 'REVIEWING', 'RESOLVED', 'REJECTED'))
);

DROP TRIGGER IF EXISTS touch_user_recipe_reports_updated_at
ON user_recipe_reports;

CREATE TRIGGER touch_user_recipe_reports_updated_at
BEFORE UPDATE ON user_recipe_reports
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE INDEX IF NOT EXISTS idx_user_recipe_reports_status_created
ON user_recipe_reports(status, report_id DESC);

CREATE INDEX IF NOT EXISTS idx_user_recipe_reports_user_recipe_id
ON user_recipe_reports(user_recipe_id);

CREATE INDEX IF NOT EXISTS idx_user_recipe_reports_reporter_user_id
ON user_recipe_reports(reporter_user_id);

CREATE INDEX IF NOT EXISTS idx_user_recipe_reports_recipe_owner_user_id
ON user_recipe_reports(recipe_owner_user_id);
