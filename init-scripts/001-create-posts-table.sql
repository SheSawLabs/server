-- Drop existing tables
DROP TABLE IF EXISTS meetups CASCADE;
DROP TABLE IF EXISTS posts CASCADE;

-- Create unified posts table
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('수리', '소분', '취미', '기타', '일반')),
    image_url VARCHAR(500),
    location VARCHAR(255),
    date TIMESTAMP WITH TIME ZONE,
    
    -- Meetup participant limits and status
    min_participants INTEGER,
    max_participants INTEGER,
    status VARCHAR(20) DEFAULT 'recruiting' CHECK (status IN ('recruiting', 'active', 'full')),
    
    -- Common fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints: 일반 카테고리가 아닌 경우 location과 date 필수
    CONSTRAINT meetup_required_fields 
        CHECK (
            (category = '일반') OR 
            (category != '일반' AND location IS NOT NULL AND date IS NOT NULL AND min_participants IS NOT NULL AND max_participants IS NOT NULL)
        ),
    
    -- Participant limits validation
    CONSTRAINT participant_limits_check
        CHECK (
            (category = '일반') OR
            (min_participants > 0 AND max_participants > 0 AND min_participants <= max_participants)
        )
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date) WHERE category != '일반';
CREATE INDEX IF NOT EXISTS idx_posts_location ON posts(location) WHERE category != '일반';
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status) WHERE category != '일반';