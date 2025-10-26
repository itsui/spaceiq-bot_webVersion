# Quick Start Guide

## TL;DR - Just Run This

```bash
# Headless mode (no browser window) - RECOMMENDED
python multi_date_book.py --auto --headless

# OR double-click this:
run_headless_booking.bat
```

That's it! Books all your Wed/Thu dates in priority order, in the background.

---

## All Available Commands

### Standard Booking (Shows Browser)
```bash
python multi_date_book.py --auto
```

### Headless Booking (No Browser Window)
```bash
python multi_date_book.py --auto --headless
```

### Polling Mode (Keeps Trying Until Booked)
```bash
python multi_date_book.py --auto --headless --poll
```

### All-in-One (Warm Session + Book)
```bash
# With browser window (for first time / expired session)
python quick_book.py --auto

# Headless mode
python quick_book.py --auto --headless
```

---

## Your Current Setup

### Desk Priorities (Already Configured)
1. **Best:** 2.24.01 to 2.24.20
2. **Second:** 2.24.34 to 2.24.42
3. **Third:** 2.24.52 to 2.24.68
4. **Fourth:** 2.24.22 to 2.24.33
5. **Last Resort:** 2.24.44 to 2.24.46

Bot will ALWAYS try Priority 1 first!

### Locked Desks (Automatically Excluded)
- Configured in `config/locked_desks.json`
- Bot never books these, even if Priority 1

---

## Common Scenarios

### First Time Setup
```bash
# 1. Warm session (need visible browser for SSO)
python auto_warm_session.py

# 2. Run booking in headless mode
python multi_date_book.py --auto --headless
```

### Daily/Weekly Booking
```bash
# Just run this (session already warmed)
python multi_date_book.py --auto --headless

# OR
run_headless_booking.bat
```

### Session Expired?

**NEW: Automatic Handling!**

If session expires and you run in headless mode:
1. Bot detects expired session automatically
2. Opens visible browser window for you to login
3. After you login, browser closes
4. Booking resumes in headless mode automatically!

```bash
# Just run this - bot handles session expiry automatically!
python multi_date_book.py --auto --headless

# OR
run_headless_booking.bat
```

**Old manual way (still works):**
```bash
# 1. Warm session manually
python auto_warm_session.py

# 2. Resume headless booking
python multi_date_book.py --auto --headless
```

### No Seats Available?
```bash
# Enable polling mode (keeps trying)
python multi_date_book.py --auto --headless --poll
```

---

## Flags Reference

| Flag | What It Does |
|------|--------------|
| `--auto` | Auto-generate Wed/Thu dates for next 29 days |
| `--headless` | Run without browser window (background) |
| `--poll` | Keep trying until at least one seat booked |
| `--unattended` | No prompts (for scheduled tasks) |

### Combine Flags
```bash
# Most powerful combo:
python multi_date_book.py --auto --headless --poll --unattended
```

This will:
- Auto-generate dates ✓
- Run in background ✓
- Keep trying until booked ✓
- No prompts ✓

---

## Scheduling (Windows Task Scheduler)

**Tuesday 11:59 PM:**
```
Program: python
Arguments: D:\SD\spaceIqBotv01\multi_date_book.py --auto --headless --unattended
```

**Wednesday 11:59 PM:**
```
Program: python
Arguments: D:\SD\spaceIqBotv01\multi_date_book.py --auto --headless --unattended
```

This books Wed/Thu seats automatically every week, in the background!

---

## Troubleshooting

### "Session expired"
```bash
python auto_warm_session.py
```

### "No available desks"
```bash
# Enable polling to keep trying
python multi_date_book.py --auto --headless --poll
```

### Want to see what's happening?
```bash
# Remove --headless flag
python multi_date_book.py --auto
```

### Test priorities without booking
```bash
python test_features.py
```

---

## What Changed From Stable Version?

### v1.0-stable (Old)
- Had to edit .env file for headless mode
- Booked first available desk (random)
- No priorities

### Current (New)
- Just add `--headless` flag (much easier!)
- Books highest priority desk (smart!)
- Respects your preferences

---

**Most Common Usage:**

```bash
python multi_date_book.py --auto --headless
```

Or just double-click: `run_headless_booking.bat`

Done! 🎉
