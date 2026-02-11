CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Защищенный ID
    email VARCHAR(255) UNIQUE NOT NULL,            -- Логин/Email
    password_hash VARCHAR(255) NOT NULL,           -- Хеш Argon2 (не сам пароль!)
    
    -- Роли и Доступ
    role VARCHAR(50) DEFAULT 'user',               -- 'user', 'admin', 'support'
    is_active BOOLEAN DEFAULT TRUE,                -- Если FALSE — вход заблокирован (бан)
    is_verified BOOLEAN DEFAULT FALSE,             -- Подтвердил ли почту
    
    -- Безопасность (2FA)
    totp_secret VARCHAR(255),                      -- Секрет для Google Authenticator
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    
    -- Метаданные
    telegram_id VARCHAR(50),                       -- Для уведомлений в телегу
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Индекс для молниеносного поиска при входе
CREATE INDEX idx_users_email ON users(email);