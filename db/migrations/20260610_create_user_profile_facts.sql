CREATE TABLE user_profile_facts (
    fact_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    field VARCHAR(50) NOT NULL,
    canonical_value VARCHAR(255) NOT NULL,
    display_value VARCHAR(255) NOT NULL,
    source_type VARCHAR(30) NOT NULL
        CHECK (source_type IN ('USER_INPUT', 'CHAT', 'BACKFILL')),
    source_text VARCHAR(1000) NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, field, canonical_value, source_type, source_key)
);

CREATE INDEX idx_user_profile_facts_user
ON user_profile_facts (user_id, field);
