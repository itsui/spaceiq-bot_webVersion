-- ============================================================================
-- Supabase Tables Setup for SpaceIQ Bot User Whitelisting
-- ============================================================================
-- Run this SQL in your Supabase SQL Editor
-- Dashboard: https://abdpxfqnyywmyrqazyft.supabase.co
-- ============================================================================

-- ============================================================================
-- TABLE 1: allowed_users (Whitelist)
-- ============================================================================

-- Create table for allowed users
CREATE TABLE IF NOT EXISTS allowed_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Add your user to whitelist (replace 'fvargas' with actual username)
INSERT INTO allowed_users (username, is_active)
VALUES ('fvargas', true)
ON CONFLICT (username) DO NOTHING;

-- Enable Row Level Security
ALTER TABLE allowed_users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Allow read access to all users" ON allowed_users;

-- Allow anyone with anon key to read whitelist
CREATE POLICY "Allow read access to all users"
    ON allowed_users
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- ============================================================================
-- TABLE 2: usage_logs (Activity Tracking)
-- ============================================================================

-- Create table for usage logs
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_usage_logs_username ON usage_logs(username);
CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs(timestamp);

-- Enable Row Level Security
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Allow insert access for logging" ON usage_logs;

-- Allow anyone with anon key to insert logs (but not read/update/delete)
CREATE POLICY "Allow insert access for logging"
    ON usage_logs
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Grant explicit table permissions to anon role (CRITICAL!)
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON allowed_users TO anon;
GRANT INSERT ON usage_logs TO anon;

-- ============================================================================
-- Verify Setup
-- ============================================================================

-- Check tables exist
SELECT 'Tables created successfully!' as status;

-- Show allowed users
SELECT * FROM allowed_users;

-- Show usage logs count
SELECT COUNT(*) as total_logs FROM usage_logs;

-- ============================================================================
-- How to Add More Users
-- ============================================================================

-- Add a new user:
-- INSERT INTO allowed_users (username, is_active) VALUES ('new_username', true);

-- Deactivate a user:
-- UPDATE allowed_users SET is_active = false WHERE username = 'username_to_disable';

-- Reactivate a user:
-- UPDATE allowed_users SET is_active = true WHERE username = 'username_to_enable';

-- View all logs for a specific user:
-- SELECT * FROM usage_logs WHERE username = 'fvargas' ORDER BY timestamp DESC LIMIT 50;

-- ============================================================================
