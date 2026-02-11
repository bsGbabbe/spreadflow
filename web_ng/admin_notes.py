CREATE TABLE admin_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_user_id UUID REFERENCES users(id),      -- На кого досье
    author_admin_id UUID REFERENCES users(id),     -- Кто написал (ты или модератор)
    
    note_text TEXT NOT NULL,                       -- "Подозрительная активность, проверить IP"
    flag_color VARCHAR(20) DEFAULT 'gray',         -- 'red' (опасно), 'yellow' (внимание), 'green' (ок)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);