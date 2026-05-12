INSERT INTO users (email, password_hash, nickname, role, is_blocked)
VALUES ('yschoi9733@gmail.com', '1234', '냉고', 'ADMIN', false)
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_profiles (user_id, user_input)
VALUES (1, '[]')
ON CONFLICT (user_id) DO NOTHING;
