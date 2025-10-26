# Session Handling - Smart Auto-Recovery

## 🎯 Smart Session Management

The bot now **automatically handles expired sessions** when running in headless mode!

---

## How It Works

### Scenario 1: Session Valid (Normal Flow)

```
You run: run_headless_booking.bat
         ↓
Bot: Validating session...
Bot: Session is valid ✓
Bot: Running in HEADLESS mode (no browser window)
Bot: Booking desks...
     ↓
Done! (You never saw a browser window)
```

### Scenario 2: Session Expired (Auto-Recovery)

```
You run: run_headless_booking.bat
         ↓
Bot: Validating session...
Bot: Session expired (redirected to login page) ⚠️
Bot: Opening visible browser for re-login...
     ↓
Browser window opens automatically
     ↓
You: Login via SSO in the browser window
     ↓
Bot: Login detected! ✓
Bot: Saving session...
Bot: Closing browser...
Bot: Resuming in HEADLESS mode
Bot: Booking desks...
     ↓
Done! (Browser closed, booking happened in background)
```

---

## What You'll See

### When Session Is Valid:
```
========================================
 SpaceIQ Headless Booking (Auto)
========================================

[INFO] Headless mode requested - validating session first...
[INFO] Validating session...
[SUCCESS] Session is valid
[INFO] Browser launched

Booking desks...
```

### When Session Is Expired:
```
========================================
 SpaceIQ Headless Booking (Auto)
========================================

[INFO] Headless mode requested - validating session first...
[INFO] Validating session...
[WARNING] Session expired (redirected to login page)

======================================================================
         SESSION EXPIRED - OPENING BROWSER FOR LOGIN
======================================================================

Your session has expired. Opening browser for re-login...
After you login, the bot will continue automatically.
Booking will resume in HEADLESS mode after login.
======================================================================

[INFO] Navigating to https://main.spaceiq.com/finder/building/LC/floor/2

======================================================================
         PLEASE LOGIN
======================================================================

Browser window is now open.
Please complete these steps:
  1. Click 'Login with SSO'
  2. Enter your company email
  3. Complete SSO authentication
  4. Wait until you see the floor map

Bot will detect login automatically...
======================================================================

[SUCCESS] Login detected!
[INFO] Saving session...
[SUCCESS] Session saved to: D:\SD\spaceIqBotv01\playwright\.auth\auth.json

======================================================================
         SESSION REFRESHED - CONTINUING BOOKING
======================================================================

Resuming in HEADLESS mode (no browser window)
======================================================================

[INFO] Browser launched
Booking desks...
```

---

## Benefits

### Before (Manual Handling):
1. Run `python multi_date_book.py --auto --headless`
2. Get error: "Session expired"
3. Stop the script
4. Run `python auto_warm_session.py`
5. Login manually
6. Run `python multi_date_book.py --auto --headless` again

**6 steps, had to remember separate command**

### Now (Automatic Handling):
1. Run `run_headless_booking.bat`
2. If session expired, browser opens automatically
3. Login
4. Browser closes, booking continues

**3 steps, completely automatic!**

---

## Technical Details

### Session Validation Flow:

```python
# src/auth/session_validator.py

async def validate_and_refresh_session(force_headless: bool):
    """
    1. Check if auth.json exists
       ├─ No → Run session warmer with visible browser
       └─ Yes → Continue

    2. Quick test: Navigate to SpaceIQ in headless mode
       ├─ Redirected to /login? → Session expired
       └─ On /finder page? → Session valid

    3. If session expired:
       ├─ Launch visible browser
       ├─ Navigate to app (redirects to login)
       ├─ Wait for user to login
       ├─ Save new session
       ├─ Close browser
       └─ Return: Continue with headless mode

    4. If session valid:
       └─ Return: Continue with headless mode
    """
```

### Integration Point:

```python
# src/workflows/multi_date_booking.py

async def run(self):
    # Before launching browser
    if self.headless:
        # Validate session first
        session_valid, use_headless = await validate_and_refresh_session(
            force_headless=True
        )

        if not session_valid:
            return {}  # Failed to refresh

        # Update headless setting
        self.headless = use_headless

    # Now initialize browser (headless or visible)
    context = await self.session_manager.initialize()
    ...
```

---

## When Validation Happens

**Only when you use `--headless` flag:**

```bash
# Validates session automatically
python multi_date_book.py --auto --headless
run_headless_booking.bat

# Does NOT validate (you see browser anyway)
python multi_date_book.py --auto
```

**Why?**
- Visible mode: You'll see login page anyway if session expired
- Headless mode: You won't see anything, so we check first

---

## Error Handling

### Session Validation Failed:
```
[ERROR] Session validation failed. Cannot continue.

Troubleshooting:
1. Check internet connection
2. Verify SpaceIQ URL in .env
3. Try running: python auto_warm_session.py
```

### Login Timeout (5 minutes):
```
[ERROR] Login timeout: Timeout 300000ms exceeded

Please try again or check your SSO settings.
```

### Browser Launch Failed:
```
[ERROR] Session warming failed: Could not launch browser

Troubleshooting:
1. Ensure Chrome is installed
2. Check browser permissions
3. Try closing all Chrome windows first
```

---

## Manual Override

If you prefer manual session warming:

```bash
# Warm session manually first
python auto_warm_session.py

# Then run without validation
python multi_date_book.py --auto --headless
```

The session will still be validated, but it will be valid so no browser opens.

---

## Scheduled Runs

**Perfect for Windows Task Scheduler:**

```
Program: D:\SD\spaceIqBotv01\run_headless_booking.bat
Trigger: Tuesday 11:59 PM
```

**What happens:**
- Most runs: Session valid, runs completely headless ✓
- Occasionally: Session expired, opens browser briefly for re-login, then continues ✓

**You don't need to monitor it!** If session expires, you'll just see a browser window pop up asking you to login. After you login, it closes and continues booking automatically.

---

## Best Practices

### For Daily Use:
```bash
# Just run this - handles everything
run_headless_booking.bat
```

### For Scheduled Tasks:
```bash
# Add this to Task Scheduler
python multi_date_book.py --auto --headless --unattended
```

### For Testing:
```bash
# Use visible mode to see what's happening
python multi_date_book.py --auto
```

---

## Summary

**Old Way:**
- Session expires → Script fails → Manual intervention required

**New Way:**
- Session expires → Browser opens → You login → Script continues

**Result:** Headless mode is now truly "set it and forget it"! 🎉
