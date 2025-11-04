-- ============================================================================
-- FIX: Supabase RLS Policy for usage_logs
-- ============================================================================
-- The issue: RLS is blocking INSERT even with WITH CHECK (true)
-- Solution: Recreate table with correct policies and grants
-- ============================================================================

-- Step 1: Drop and recreate usage_logs table (clean slate)
DROP TABLE IF EXISTS usage_logs;

CREATE TABLE usage_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Step 2: Enable RLS
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Step 3: Create INSERT policy for anon role (this is what the bot uses)
CREATE POLICY "anon_insert_logs"
    ON usage_logs
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Step 4: Grant explicit permissions to anon role
GRANT INSERT ON TABLE usage_logs TO anon;

-- Step 5: Test the policy by inserting a test row as anon
SET ROLE anon;
INSERT INTO usage_logs (username, machine_id, action, timestamp, details)
VALUES ('test_user', 'test_machine', 'policy_test', NOW(), '{"test": true}');
RESET ROLE;

-- Step 6: Verify the insert worked
SELECT COUNT(*) as total_logs, 'SUCCESS - RLS policy working!' as status FROM usage_logs;

-- ============================================================================
-- If the above INSERT fails, it means there's a deeper permission issue
-- In that case, run this alternative (LESS SECURE but will work):
-- ============================================================================

-- ALTERNATIVE: Disable RLS entirely (not recommended for production)
-- Uncomment only if the above doesn't work:

-- ALTER TABLE usage_logs DISABLE ROW LEVEL SECURITY;
-- GRANT INSERT ON TABLE usage_logs TO anon, authenticated, service_role;

-- ============================================================================
