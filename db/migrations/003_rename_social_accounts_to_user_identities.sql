ALTER TABLE social_accounts RENAME TO user_identities;
ALTER INDEX idx_social_accounts_user_id RENAME TO idx_user_identities_user_id;
