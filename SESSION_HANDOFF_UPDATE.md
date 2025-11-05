# Session Debugging Update - November 5, 2025

## ✅ DEBUGGING IMPROVEMENTS ADDED (Commit: a073076)

All recommended debugging has been implemented and committed. The code now includes comprehensive logging to diagnose the session persistence issue.

---

## What Was Added

### 1. Session Save Debugging (app.py:1097-1153)

When a session is saved, the following is logged:

```
================================================================================
SESSION SAVE DEBUG
Session file exists: True
Session file size: XXXX bytes
Session structure:
  - Cookies: XX cookies
  - Origins: XX origins
Important cookies found: X
    [cookie_name] @ [domain]: [value preview] (httpOnly=True, secure=True)
    ...
  Origin: https://main.spaceiq.com
    localStorage items: X
    sessionStorage items: X
      [item_name]: [value preview]
      ...
Current URL at time of save: https://main.spaceiq.com/finder/...
================================================================================
```

**Plus automatic session validation:**
```
Testing saved session validity...
  Navigating to SpaceIQ finder page...
  Final URL: https://main.spaceiq.com/[finder OR login]
  ✅ SESSION VALID - Stayed on finder page
  OR
  ❌ SESSION INVALID - Redirected to login page!
```

### 2. Bot Session Load Debugging (bot_manager.py:78-110)

When the bot loads a session:

```
================================================================================
SESSION LOAD DEBUG
Loading session for user 1
Session data length: XXXX bytes
Session data is encrypted, decrypting...
Decrypted session data length: XXXX bytes
Successfully decrypted and parsed session data
Session structure:
  - Cookies: XX cookies
  - Origins: XX origins
Important cookies: [cookie_name @ domain, ...]
Writing session to temp file: /tmp/spaceiq_session_XXX_user1.json
Session written to temp file successfully
================================================================================
```

### 3. Session Manager Debugging (src/auth/session_manager.py:53-79)

When SessionManager loads the session:

```
[DEBUG] Loading session from: /tmp/spaceiq_session_XXX_user1.json
[DEBUG] Session loaded successfully
[DEBUG]   - Cookies: XX
[DEBUG]   - Origins: XX
[DEBUG]   - Auth cookies: [cookie_name @ domain, ...]
```

### 4. Authentication Delay (browser_stream_manager_fixed.py:192-200)

Added 3-second delay after authentication detection to allow SSO cookies to fully propagate:

```
✓ Authentication detected for user 1 at https://main.spaceiq.com/finder/...
  Waiting 3 seconds for all cookies to be set...
✓✓✓ Authentication SUCCESSFUL for user 1
```

---

## How to Use These Logs

### When User Completes SSO Authentication

**Step 1: Check Session Save Logs**

Look for the "SESSION SAVE DEBUG" block in `logs/app.log`. Answer these questions:

1. **How many cookies were saved?**
   - Expected: 10-20+ cookies
   - If < 5: SSO authentication didn't complete

2. **Are there cookies from these domains?**
   - ✅ main.spaceiq.com
   - ✅ .spaceiq.com (with leading dot)
   - ✅ okta domain (SSO provider)
   - ✅ Other auth-related domains

3. **Are there authentication cookies with these names?**
   - Look for: session, token, auth, sid, jwt, okta
   - httpOnly should be True for security

4. **Is there localStorage/sessionStorage data?**
   - SpaceIQ might store auth state in browser storage
   - Check if data exists for main.spaceiq.com origin

5. **What was the URL when session was saved?**
   - Should be: https://main.spaceiq.com/finder/...
   - If different, authentication might not be complete

**Step 2: Check Session Validation Test**

Immediately after saving, the system tests the session:

```
Testing saved session validity...
  Navigating to SpaceIQ finder page...
  Final URL: https://main.spaceiq.com/finder
  ✅ SESSION VALID - Stayed on finder page
```

**Critical Decision Point:**

- If ✅ **SESSION VALID**: The issue is with session loading/usage by the bot
- If ❌ **SESSION INVALID**: The issue is with session capture itself

**Step 3: If Bot Still Fails, Check Session Load Logs**

Look for "SESSION LOAD DEBUG" in `logs/app.log` when bot starts:

1. **Does cookie count match what was saved?**
   - If different: encryption/decryption issue

2. **Are the same auth cookies present?**
   - If missing: data corruption or wrong decryption key

3. **Did SessionManager load the session?**
   - Check [DEBUG] logs from SessionManager
   - Should show same cookie count

---

## Root Cause Analysis Guide

Based on the logs, identify which scenario applies:

### Scenario A: Session Validation Fails Immediately (❌)

**Symptoms:**
- Few cookies saved (< 5)
- No okta or auth cookies
- Session validation test fails right after save

**Root Cause:**
SSO authentication not fully completing before session saved

**Fix Options:**

1. **Increase delay (Quick)**
   ```python
   # browser_stream_manager_fixed.py line 197
   await asyncio.sleep(10)  # Was 3, try 10
   ```

2. **Wait for specific cookie (Better)**
   ```python
   async def wait_for_auth_complete(self):
       for _ in range(40):  # 20 seconds max
           cookies = await self.context.cookies()
           # Look for specific SpaceIQ session cookie
           if any('session' in c['name'].lower() and 'spaceiq' in c['domain']
                  for c in cookies):
               return True
           await asyncio.sleep(0.5)
       return False

   # Use instead of sleep:
   if await self.wait_for_auth_complete():
       self.authenticated = True
   ```

3. **Wait for specific network activity (Best)**
   ```python
   # Wait for final API call that sets auth cookies
   await self.page.wait_for_response(
       lambda response: 'api/session' in response.url or 'api/user' in response.url,
       timeout=10000
   )
   await asyncio.sleep(2)  # Extra buffer
   ```

### Scenario B: Session Valid But Bot Fails (✅ then ❌)

**Symptoms:**
- Many cookies saved (10-20+)
- Auth cookies present
- Session validation passes
- Bot still reports "Session expired"

**Root Cause:**
Session not being applied correctly to bot's browser context

**Fix Options:**

1. **Verify session right before bot uses it**
   ```python
   # In bot_manager.py after writing temp file:
   from src.auth.session_manager import SessionManager
   import asyncio

   async def verify_bot_session():
       test_sm = SessionManager(auth_file=str(session_file))
       test_context = await test_sm.initialize()
       test_page = await test_context.new_page()
       await test_page.goto("https://main.spaceiq.com/finder")
       final_url = test_page.url
       logger.info(f"PRE-BOT SESSION TEST: {final_url}")
       await test_sm.close()
       return '/login' not in final_url

   loop = asyncio.new_event_loop()
   is_valid = loop.run_until_complete(verify_bot_session())
   loop.close()

   if not is_valid:
       raise Exception("Session invalid right before bot use!")
   ```

2. **Use persistent context instead of storage_state**
   ```python
   # Instead of new_context with storage_state:
   # Use launch_persistent_context with user_data_dir
   ```

### Scenario C: Cookie Domain Mismatch

**Symptoms:**
- Cookies saved but have wrong domain
- Example: .spaceiq.com vs main.spaceiq.com

**Root Cause:**
Playwright cookie capture domain handling

**Fix:**
```python
# After loading session, fix domains:
for cookie in session_json.get('cookies', []):
    if cookie.get('domain') == '.spaceiq.com':
        cookie['domain'] = 'main.spaceiq.com'
```

### Scenario D: Encryption/Decryption Corruption

**Symptoms:**
- Different cookie count between save and load
- JSON parse errors
- Decryption succeeds but data looks wrong

**Fix:**
```python
# Test encryption round-trip:
from src.utils.auth_encryption import encrypt_data, decrypt_data
test_data = "test string"
encrypted = encrypt_data(test_data)
decrypted = decrypt_data(encrypted)
assert test_data == decrypted
```

---

## Quick Testing Guide

### Test 1: Complete Auth Flow

1. User logs in via browser stream
2. Watch logs for "SESSION SAVE DEBUG"
3. Check session validation result
4. If valid, start bot
5. Watch logs for "SESSION LOAD DEBUG"
6. Check if bot stays logged in

### Test 2: Manual Session Verification

```bash
# After user completes auth, check database:
sqlite3 spaceiq_multiuser.db

SELECT
    user_id,
    last_validated,
    is_valid,
    LENGTH(session_data) as size
FROM spaceiq_session;

# Should show recent timestamp and large size (>5000 bytes)
```

### Test 3: Compare with Working Session

If you have a working local session:

```python
# Load both sessions and compare
working_session = load_encrypted_session('working_auth.json')
stream_session = load_encrypted_session('stream_auth.json')

print(f"Working cookies: {len(working_session['cookies'])}")
print(f"Stream cookies: {len(stream_session['cookies'])}")

# Find missing cookies
working_cookie_names = {c['name'] for c in working_session['cookies']}
stream_cookie_names = {c['name'] for c in stream_session['cookies']}

missing = working_cookie_names - stream_cookie_names
print(f"Missing in stream: {missing}")
```

---

## Expected Timeline

With this debugging in place:

1. **Diagnosis: 10-30 minutes**
   - User completes one auth attempt
   - Review logs
   - Identify which scenario applies

2. **Fix Implementation: 30-60 minutes**
   - Apply appropriate fix based on scenario
   - Test with user

3. **Verification: 10 minutes**
   - User completes auth
   - Bot runs successfully
   - No "Session expired" error

**Total: 1-2 hours to resolution**

---

## Files Modified in This Session

```
app.py                              - Added session save debugging and validation test
bot_manager.py                      - Added session load debugging
src/auth/session_manager.py        - Added session manager debugging
browser_stream_manager_fixed.py    - Added 3s delay after auth detection
```

All changes committed to: `claude/fix-browser-stream-session-persistence-011CUpwtkVF5yjQyV4RHXqnn`

---

## Next Steps

1. **User should complete ONE authentication attempt**
2. **Review logs following this guide**
3. **Identify which scenario (A, B, C, or D)**
4. **Apply corresponding fix**
5. **Test again**

The logs will tell us exactly what's wrong!
