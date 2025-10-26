# Claude Session Notes - SpaceIQ Bot

**Last Updated:** 2025-10-26 (Evening - After Cleanup)
**Status:** 🔴 BLOCKED - SpaceIQ SSO is broken (not our code's fault)
**Project Status:** ✅ CLEANED - Old files archived, project organized

---

## Current Issue: SSO Login Broken

### Problem
- SSO login redirects to `https://main.spaceiq.com/login?redirectTo=/undefined`
- This happens in **NORMAL Chrome** too (not just our automation)
- **Root Cause:** SpaceIQ website or company SSO configuration issue

### What We Discovered
1. Initially thought it was our automation causing the issue
2. After debugging, discovered SSO is broken even in normal Chrome browser
3. **Conclusion:** This is a SpaceIQ website bug or company SSO config change, NOT our code

### User is Investigating
- Checking with company IT/colleagues if SSO changed
- Testing if SpaceIQ has a known issue
- Will report back once SSO works in normal Chrome again

---

## Project Cleanup (Oct 26, 2025)

We cleaned up the project to remove clutter and improve organization:

### ✅ Archived to `_archived_scripts/`
- **8 old scripts** moved (not deleted, kept for reference):
  - Test scripts: `check_status.py`, `quick_test.py`, `test_blue_circles.py`, `test_setup.py`
  - Debug scripts: `inspect_and_record.py`
  - Deprecated scripts: `smart_book.py`
  - Old main scripts: `main.py`, `main_spaceiq.py`
- **Why:** These were used during development but superseded by current scripts
- **Location:** `_archived_scripts/` folder with README.txt explaining what's there

### 🗑️ Deleted
- **17 old markdown files** - duplicate/outdated documentation
- **sidebar.txt** - 168KB debug output file
- **Old logs** - All logs older than 2 days removed

### ✅ Current Clean Structure
```
spaceIqBotv01/
├── warm_session.py              ⭐ Session warmer (manual Chrome + CDP)
├── multi_date_book.py           ⭐ Main booking script
├── polling_book.py              ⭐ Polling booking script
├── config.py                    ⚙️ Configuration
├── setup.py                     ⚙️ Installation setup
├── run.bat                      🎯 Main menu launcher
├── run_auto_booking.bat         🎯 Auto booking launcher
├── run_manual_booking.bat       🎯 Manual booking launcher
├── run_session_warmer.bat       🎯 Session warmer launcher
├── README.md                    📖 Main documentation
├── CLAUDE_SESSION_NOTES.md      📖 This file (session status)
├── requirements.txt             📦 Python dependencies
├── .env                         🔐 Environment config
├── src/                         📁 All source code modules
├── config/                      📁 Config files (booking_config.json, locked_desks.json)
├── logs/                        📁 Recent logs only (auto-cleanup >2 days)
├── screenshots/                 📁 Debug screenshots
├── playwright/.auth/            📁 Saved sessions & browser profile
└── _archived_scripts/           📁 Old scripts (for reference)
```

---

## What We Fixed Today

### 1. Fixed `warm_session.py`
**File:** `warm_session.py`
**Change:** Simplified to use manual Chrome launch via CDP (same approach as original `capture_session.py`)
- Uses `--remote-debugging-port=9222`
- User manually controls navigation and SSO login
- Script just connects and captures session
- **Why:** Avoids any automation interference with SSO flow

### 2. Fixed `.env` Configuration
**File:** `.env`
**Change:** Fixed `SPACEIQ_URL` to base URL only
- **Before:** `SPACEIQ_URL=https://main.spaceiq.com/finder/building/LC/floor/2`
- **After:** `SPACEIQ_URL=https://main.spaceiq.com`
- **Why:** Code was appending path again, creating malformed URLs

### 3. Fixed Login Detection Logic
**File:** `src/pages/spaceiq_booking_page.py:47-58`
**Change:** Fixed `check_and_wait_for_login()` to properly wait for login completion
- **Before:** `wait_for_url("**/finder/building/**")` - matched too early
- **After:** `wait_for_url(lambda url: "/login" not in url and "/finder/building/" in url)`
- **Why:** Login page URL contained `/finder/building/` in redirect param, causing false positive

---

## How the System Works

### Authentication Flow
1. **Initial Setup (first time):**
   - Run `python src/auth/capture_session.py`
   - Manually launch Chrome with CDP
   - Login via SSO manually
   - Script captures session to `playwright/.auth/auth.json`

2. **Session Warming (when expired):**
   - Run `python warm_session.py`
   - Same manual approach as capture_session
   - Refreshes the saved session

3. **Automated Booking:**
   - Run `python multi_date_book.py` or `python polling_book.py`
   - Uses saved session from `playwright/.auth/auth.json`
   - If session expires, user must run warm_session.py again

### Key Files
- **`warm_session.py`** - Session refresh script (manual Chrome + CDP)
- **`src/auth/capture_session.py`** - Original session capture (same approach)
- **`playwright/.auth/auth.json`** - Saved session state (cookies, tokens)
- **`playwright/.auth/browser_profile/`** - Persistent browser profile for SSO
- **`.env`** - Configuration (SPACEIQ_URL, CDP_PORT, etc.)

### Important Config
- **SPACEIQ_URL:** `https://main.spaceiq.com` (base URL only!)
- **CDP_PORT:** `9222`
- **Target Page:** `https://main.spaceiq.com/finder/building/LC/floor/2`
- **Building:** LC, **Floor:** 2, **Desk Prefix:** 2.24.*

---

## Next Steps (When SSO is Fixed)

1. **Verify SSO works in normal Chrome:**
   - Navigate to `https://main.spaceiq.com`
   - Click "Login with SSO"
   - Enter company email
   - Should redirect to company SSO page (NOT `/undefined`)

2. **Once SSO works, re-capture session:**
   ```bash
   # Kill any running Chrome
   taskkill /F /IM chrome.exe

   # Clean old session data
   rm -rf playwright/.auth/browser_profile
   rm -f playwright/.auth/auth.json

   # Run warm_session to capture fresh session
   python warm_session.py
   ```

3. **Test booking scripts:**
   ```bash
   python multi_date_book.py
   ```

---

## Common Issues Reference

### Issue: `/undefined` redirect during SSO
- **Cause:** SpaceIQ website bug or SSO config issue
- **Test:** Try SSO in normal Chrome - if broken there too, it's not our code
- **Fix:** Wait for SpaceIQ/IT to fix SSO

### Issue: "Session expired" but can't re-login
- **Cause:** Corrupted browser profile
- **Fix:** Clean browser profile and auth.json, start fresh

### Issue: Playwright automation detected
- **Fix:** Use manual Chrome launch with CDP (current approach)

### Issue: Chrome won't connect via CDP
- **Cause:** Chrome not launched with `--remote-debugging-port=9222`
- **Fix:** Ensure Chrome command includes the port flag

---

## Files Modified/Changed in This Session

### Code Fixes
1. **`warm_session.py`** - Complete rewrite to manual CDP approach (same as capture_session.py)
2. **`.env`** - Fixed SPACEIQ_URL to base URL only (was causing malformed URLs)
3. **`src/pages/spaceiq_booking_page.py`** - Fixed login detection logic (line 47-58)

### Project Cleanup
4. **Archived** - Moved 8 old scripts to `_archived_scripts/` folder
5. **Deleted** - Removed 17 old markdown files, sidebar.txt, and logs >2 days old
6. **Created** - `CLAUDE_SESSION_NOTES.md` (this file) and `_archived_scripts/README.txt`

---

## User Context

- **User:** Felipe
- **Company:** Uses SSO for SpaceIQ login
- **Goal:** Automate desk booking for Building LC, Floor 2
- **Booking Strategy:** Multi-date booking, runs at 11:59 PM for next day
- **Preferred Desks:** 2.24.* prefix (not locked/permanent desks)

---

## Important Notes

- ✅ **Original `capture_session.py` worked perfectly** - SSO was fine initially
- ✅ **warm_session.py now uses SAME approach** - manual Chrome + CDP
- 🔴 **SSO broke externally** - nothing wrong with our automation
- 📌 **Always test SSO in normal Chrome first** before debugging automation

---

## Maintaining Clean Project

To keep the project organized:

1. **Old logs auto-cleanup:** Logs older than 2 days can be manually deleted anytime
   ```bash
   find logs/ -name "*.log" -type f -mtime +2 -delete
   ```

2. **Archive unused scripts:** If you create test scripts, move them to `_archived_scripts/` when done

3. **Don't create new markdown files:** Add notes to this file or README.md instead

4. **Keep root clean:** Only essential .py and .bat files in root directory

---

**REMEMBER:** If user reports SSO issues, FIRST ask them to test in normal Chrome to determine if it's a website/SSO issue vs automation issue.
