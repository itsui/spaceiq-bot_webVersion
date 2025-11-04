-- ============================================================================
-- SIMPLE FIX: Disable RLS for usage_logs
-- ============================================================================
-- Since usage_logs is just for tracking/logging, not access control,
-- we can safely disable RLS. The security layer is in allowed_users.
-- ============================================================================

-- Disable RLS on usage_logs (security is handled by allowed_users whitelist)
ALTER TABLE usage_logs DISABLE ROW LEVEL SECURITY;

-- Grant permissions to all roles
GRANT INSERT ON TABLE usage_logs TO anon, authenticated, service_role;

-- Verify by inserting a test log
INSERT INTO usage_logs (username, machine_id, action, timestamp, details)
VALUES ('test_disable_rls', 'test_machine', 'rls_disabled_test', NOW(), '{"test": true}');

-- Check it worked
SELECT COUNT(*) as total_logs, 'RLS disabled - inserts working!' as status FROM usage_logs;

-- ============================================================================
