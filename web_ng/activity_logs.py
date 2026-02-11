CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    
    action VARCHAR(100) NOT NULL,                  -- 'login', 'change_password', 'export_data'
    ip_address INET,                               -- IP адрес (Postgres умеет их хранить эффективно)
    user_agent TEXT,                               -- Браузер и устройство (Chrome, iPhone и т.д.)
    
    details JSONB,                                 -- Гибкое поле для деталей (например: "изменил спред с 1% на 2%")
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс, чтобы админка не тормозила при просмотре логов
CREATE INDEX idx_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_logs_created_at ON activity_logs(created_at);