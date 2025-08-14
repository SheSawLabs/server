-- Drop existing settlement tables and recreate with simplified schema
DROP TABLE IF EXISTS settlement_participants CASCADE;
DROP TABLE IF EXISTS settlement_requests CASCADE;

-- Create simplified settlement requests table
CREATE TABLE IF NOT EXISTS settlement_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    creator_id INTEGER NOT NULL,
    total_amount INTEGER NOT NULL CHECK (total_amount > 0),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create settlement participants table (who needs to pay)
CREATE TABLE IF NOT EXISTS settlement_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_request_id UUID NOT NULL REFERENCES settlement_requests(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')),
    toss_payment_key VARCHAR(255),
    toss_order_id VARCHAR(255),
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate settlement participation
    UNIQUE(settlement_request_id, user_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_settlement_requests_post_id ON settlement_requests(post_id);
CREATE INDEX IF NOT EXISTS idx_settlement_requests_creator_id ON settlement_requests(creator_id);
CREATE INDEX IF NOT EXISTS idx_settlement_requests_status ON settlement_requests(status);
CREATE INDEX IF NOT EXISTS idx_settlement_requests_created_at ON settlement_requests(created_at);

CREATE INDEX IF NOT EXISTS idx_settlement_participants_settlement_id ON settlement_participants(settlement_request_id);
CREATE INDEX IF NOT EXISTS idx_settlement_participants_user_id ON settlement_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_settlement_participants_payment_status ON settlement_participants(payment_status);
CREATE INDEX IF NOT EXISTS idx_settlement_participants_toss_order_id ON settlement_participants(toss_order_id);

-- Update trigger for updated_at timestamp
CREATE TRIGGER update_settlement_requests_updated_at
    BEFORE UPDATE ON settlement_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settlement_participants_updated_at
    BEFORE UPDATE ON settlement_participants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();