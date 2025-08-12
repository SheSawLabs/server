-- Create meetup participants table
CREATE TABLE IF NOT EXISTS meetup_participants (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate participation (same user for same meetup)
    UNIQUE(post_id, user_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_participants_post_id ON meetup_participants(post_id);
CREATE INDEX IF NOT EXISTS idx_participants_joined_at ON meetup_participants(joined_at);