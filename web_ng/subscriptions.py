CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- Связь с юзером
    
    plan_type VARCHAR(50) NOT NULL,                -- 'free', 'pro', 'enterprise'
    status VARCHAR(50) NOT NULL,                   -- 'active', 'expired', 'cancelled'
    
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_date TIMESTAMP WITH TIME ZONE,             -- Когда подписка сгорит
    
    auto_renew BOOLEAN DEFAULT TRUE                -- Автопродление
);