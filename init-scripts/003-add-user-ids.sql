-- Add user_id columns to existing tables
-- This migration adds user_id references to posts, comments, and likes tables

-- First, create users table if not exists (should already exist from auth system)
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

-- Add author_id to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS author_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

-- Add author_id to comments table  
ALTER TABLE comments ADD COLUMN IF NOT EXISTS author_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

-- Add user_id to likes table
ALTER TABLE likes ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

-- Add user_id to comment_likes table
ALTER TABLE comment_likes ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

-- Create indexes for new foreign keys
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id);
CREATE INDEX IF NOT EXISTS idx_comment_likes_user_id ON comment_likes(user_id);

-- Update constraints for likes to use user_id instead of user_name
ALTER TABLE likes DROP CONSTRAINT IF EXISTS likes_post_id_user_name_key;
ALTER TABLE likes ADD CONSTRAINT likes_post_id_user_id_unique UNIQUE(post_id, user_id);

-- Update constraints for comment_likes to use user_id instead of user_name  
ALTER TABLE comment_likes DROP CONSTRAINT IF EXISTS comment_likes_comment_id_user_name_key;
ALTER TABLE comment_likes ADD CONSTRAINT comment_likes_comment_id_user_id_unique UNIQUE(comment_id, user_id);