# SpaceIQ Booking Bot - Phase 1

An AI-powered automation bot for SpaceIQ booking platform using a hybrid DOM-based and visual recognition approach.

## Project Structure

```
spaceIqBotv01/
├── src/
│   ├── auth/              # Authentication modules
│   ├── pages/             # Page Object Model classes
│   ├── workflows/         # Booking workflow implementations
│   └── utils/             # Helper utilities
├── playwright/.auth/      # Authentication state (DO NOT COMMIT)
├── config.py              # Configuration management
└── main.py                # Main entry point
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your SpaceIQ URL:

```bash
cp .env.example .env
```

Edit `.env` and set your SpaceIQ instance URL.

### 3. First-Time Authentication (MANUAL STEP REQUIRED)

The bot requires a one-time manual login to capture your authenticated session:

```bash
python src/auth/capture_session.py
```

**Follow these steps:**
1. The script will provide a Chrome launch command
2. Copy and run that command in your terminal
3. In the opened browser, manually complete SSO/2FA login
4. Return to the Python script and press Enter
5. Your session will be saved to `playwright/.auth/auth.json`

### 4. Run the Bot

After authentication is captured:

```bash
python main.py
```

## Session Management

- Your authentication session is stored in `playwright/.auth/auth.json`
- This file contains sensitive session tokens and is git-ignored
- Re-run `capture_session.py` when your session expires (typically every few days/weeks)

## Features

### Core Booking
- ✅ CDP-based authentication capture
- ✅ Persistent session management with storageState
- ✅ Session expiration detection with manual login prompt
- ✅ Page Object Model architecture
- ✅ Resilient selector strategy (Role > TestId > CSS)

### Advanced Features
- ✅ **Computer Vision-based desk detection** (OpenCV blue circle detection)
- ✅ **Multi-date booking** with automatic success tracking
- ✅ **Auto mode** - generates Wed/Thu dates for next 4 weeks+1
- ✅ **Smart booking order** - books furthest dates first (most available)
- ✅ **Configurable locked desks** (via JSON)
- ✅ **Session warming** for scheduled runs

## Quick Start

### Manual Booking
```bash
# Edit config/booking_config.json with your desired dates
python multi_date_book.py
```

### Auto Mode (Recommended)
Automatically generates and books all Wednesday/Thursday dates for the next 4 weeks+1:

```bash
# Interactive mode (prompts for confirmation)
python multi_date_book.py --auto

# Unattended mode (no prompts, for scheduled tasks)
python multi_date_book.py --auto --unattended
```

### Session Warmer (For Scheduled Runs)
Run this before scheduled booking to ensure session is fresh:

```bash
# NEW: Fully automated - no manual terminal commands needed!
python auto_warm_session.py

# Legacy method (requires manual Chrome launch in separate terminal)
python warm_session.py
```

### Quick Booking (All-in-One)
Automatically warm session and book in one command:

```bash
# Quick book with auto-generated Wed/Thu dates
python quick_book.py --auto

# Quick book in headless mode (no browser window)
python quick_book.py --auto --headless

# Quick book with polling (keeps trying until seats found)
python quick_book.py --auto --poll --headless

# Use existing session without warming
python quick_book.py --auto --skip-warm --headless
```

### Headless Mode (Background Booking)
Run booking without showing browser window:

```bash
# Add --headless flag to any booking command
python multi_date_book.py --auto --headless

# Or use the batch file
run_headless_booking.bat
```

## Scheduling for Automatic Booking

SpaceIQ allows booking **4 weeks + 1 day (29 days)** in advance.

**Recommended schedule:**
```bash
# Option 1: All-in-one (recommended for simplicity)
- **Tuesday 11:59 PM:** python quick_book.py --auto
- **Wednesday 11:59 PM:** python quick_book.py --auto

# Option 2: Separate warming (recommended for reliability)
- **Tuesday 8:00 PM:** python auto_warm_session.py (warm session)
- **Tuesday 11:59 PM:** python multi_date_book.py --auto --unattended (book Wed seats)
- **Wednesday 11:59 PM:** python multi_date_book.py --auto --unattended (book Thu seats)
```

See [SCHEDULING.md](SCHEDULING.md) for detailed setup instructions with Windows Task Scheduler.

## Configuration Files

### booking_config.json
Main booking configuration (auto-managed by bot):
```json
{
  "dates_to_try": ["2024-11-21", "2024-11-20", ...],  // Pending
  "booked_dates": ["2024-11-12", ...],                // Successful
  "desk_preferences": {"prefix": "2.24"}
}
```

### locked_desks.json
Permanently unavailable desks (edit manually):
```json
{
  "locked_desks": {
    "2.24": ["2.24.01", "2.24.13", ...]
  }
}
```

See [config/README.md](config/README.md) for editing instructions.
