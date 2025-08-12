-- Create users table for authentication (if not exists from auth system)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL DEFAULT 'kakao',
    provider_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    nickname VARCHAR(255),
    profile_image VARCHAR(500),
    thumbnail_image VARCHAR(500),
    gender VARCHAR(10),
    birthday VARCHAR(10),
    birthyear VARCHAR(4),
    age_range VARCHAR(20),
    mobile VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(provider, provider_id)
);