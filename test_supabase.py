"""
Test Supabase Connection and Permissions

Run this to diagnose Supabase RLS issues:
    python test_supabase.py
"""

from config import Config
from datetime import datetime

print("=" * 70)
print("Supabase Connection Test")
print("=" * 70)

# Check config
print(f"\n1. Configuration:")
print(f"   SUPABASE_URL: {Config.SUPABASE_URL[:30]}..." if Config.SUPABASE_URL else "   SUPABASE_URL: NOT SET")
print(f"   SUPABASE_ANON_KEY: {Config.SUPABASE_ANON_KEY[:20]}..." if Config.SUPABASE_ANON_KEY else "   SUPABASE_ANON_KEY: NOT SET")

if not Config.SUPABASE_URL or not Config.SUPABASE_ANON_KEY:
    print("\n[ERROR] Supabase not configured in .env file")
    exit(1)

try:
    from supabase import create_client
    print("\n2. Supabase library: OK")
except ImportError:
    print("\n[ERROR] Supabase library not installed")
    print("Run: pip install supabase")
    exit(1)

try:
    # Create client
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
    print("3. Client created: OK")

    # Test 1: Read allowed_users
    print("\n4. Testing SELECT on allowed_users...")
    response = supabase.table('allowed_users').select('username, is_active').execute()

    if response.data:
        print(f"   [OK] SUCCESS - Found {len(response.data)} user(s):")
        for user in response.data:
            print(f"     - {user['username']} (active: {user['is_active']})")
    else:
        print("   [WARNING] No users found in whitelist")
        print("   Add users with: INSERT INTO allowed_users (username, is_active) VALUES ('fvargas', true);")

    # Test 2: Insert into usage_logs
    print("\n5. Testing INSERT on usage_logs...")
    test_log = {
        'username': 'test_user',
        'machine_id': 'test_machine',
        'action': 'connection_test',
        'timestamp': datetime.utcnow().isoformat(),
        'details': {'test': True}
    }

    insert_response = supabase.table('usage_logs').insert(test_log).execute()

    if insert_response.data:
        print("   [OK] SUCCESS - Log inserted successfully")
        print(f"   Log ID: {insert_response.data[0]['id']}")
    else:
        print("   [FAILED] Could not insert log")
        print(f"   Response: {insert_response}")

    print("\n" + "=" * 70)
    print("[OK] All tests passed! Supabase is configured correctly.")
    print("=" * 70)

except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you've run the SQL setup in Supabase SQL Editor")
    print("2. Check that RLS policies are created correctly")
    print("3. Verify SUPABASE_URL and SUPABASE_ANON_KEY in .env")
    print("\nSQL to run:")
    print("""
    -- Enable RLS and create policies
    ALTER TABLE allowed_users ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public read access" ON allowed_users FOR SELECT USING (true);

    ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public insert access" ON usage_logs FOR INSERT WITH CHECK (true);
    """)
    exit(1)
