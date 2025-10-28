# SpaceIQ Desk Booking Bot

Automated desk booking system for SpaceIQ platform. Books desks automatically based on your preferences and schedule.

## What Does This Bot Do?

- **Automatically books desks** on SpaceIQ for your configured dates and preferences
- **Smart seat selection** based on your priority preferences
- **Continuous monitoring** for available seats (headless mode)
- **Multi-date booking** - book multiple days at once
- **Respects locked desks** and avoids unavailable seats

---

## Prerequisites

Before you start, make sure you have:

1. **Python 3.8 or higher** installed on your computer
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Git** installed (to download the project)
   - Download from: https://git-scm.com/downloads

3. **SpaceIQ account** with valid credentials

---

## Installation

### Step 1: Download the Project

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
git clone https://github.com/YOUR_USERNAME/spaceIqBotv01.git
cd spaceIqBotv01
```

### Step 2: Install Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

Install Playwright browser:

```bash
playwright install chromium
```

**Note:** If `pip` doesn't work, try `pip3` or `python -m pip` instead.

---

## First-Time Setup

### 1. Login and Save Your Session

Before using the bot, you need to login to SpaceIQ once:

**On Windows:**
```bash
run_session_warmer.bat
```

**On Mac/Linux:**
```bash
python warm_session.py
```

**What happens:**
1. A browser window will open
2. Login to SpaceIQ with your credentials (including 2FA if required)
3. Once logged in, the bot will save your session
4. You can close the browser

**Important:** Your session is saved locally in `playwright/.auth/auth.json`. Keep this file private!

---

## Configuration

### Edit Your Booking Preferences

Open `config/booking_config.json` in any text editor and configure:

#### 1. Building and Floor
```json
"building": "LC",
"floor": "2"
```
Change to your building code and floor number.

#### 2. Desk Area
```json
"desk_preferences": {
  "prefix": "2.24"
}
```
Change `"2.24"` to your preferred desk area prefix.

#### 3. Seat Priorities
```json
"priority_ranges": [
  {
    "range": "2.24.01-2.24.20",
    "priority": 1,
    "reason": "Best area - most preferred"
  },
  {
    "range": "2.24.21-2.24.40",
    "priority": 2,
    "reason": "Second choice"
  }
]
```
- **Priority 1** = Most preferred seats (tries these first)
- **Priority 2** = Second choice (tries if priority 1 unavailable)
- **Priority 3+** = Lower priorities

Add as many priority ranges as you want.

#### 4. Booking Days
```json
"booking_days": {
  "weekdays": [2, 3]
}
```
- `0` = Monday
- `1` = Tuesday
- `2` = Wednesday
- `3` = Thursday
- `4` = Friday

Default is `[2, 3]` for Wednesday and Thursday.

#### 5. Wait Times Between Rounds
```json
"wait_times": {
  "rounds_1_to_5": { "seconds": 60 },
  "rounds_6_to_15": { "seconds": 300 },
  "rounds_16_plus": { "seconds": 900 }
}
```
- Early rounds check every minute (aggressive)
- Middle rounds check every 5 minutes
- Later rounds check every 15 minutes

Change these values if you want different timing.

**See `config/README.md` for detailed configuration documentation.**

---

## How to Use

### Mode 1: One-Time Booking (Visible Browser)

Books desks once and shows the browser window (useful for testing).

**Windows:**
```bash
run.bat
```

**Mac/Linux:**
```bash
python multi_date_book.py
```

### Mode 2: Continuous Headless Booking (Recommended)

Runs continuously in the background, automatically booking available desks.

**Windows:**
```bash
run_headless_booking.bat
```

**Mac/Linux:**
```bash
python multi_date_book.py --headless
```

**What it does:**
- Checks for available desks on your configured weekdays
- Books desks automatically when available
- Runs 24/7 in the background
- Uses progressive wait times (checks frequently at first, then slows down)

**To stop:** Press `Ctrl+C`

---

## Advanced Features

### Building Position Cache

Speeds up desk selection by pre-caching desk positions:

```bash
build_position_cache.bat
```

This creates `config/desk_positions.json` with position data for faster booking.

### Locked Desks

Edit `config/locked_desks.json` to specify desks that should never be booked:

```json
{
  "locked_desks": {
    "2.24": [
      "2.24.01",
      "2.24.13"
    ]
  }
}
```

---

## Troubleshooting

### "Session expired" or "Login required"

Your session has expired. Run the session warmer again:

```bash
run_session_warmer.bat
```

### "Module not found" errors

Install dependencies again:

```bash
pip install -r requirements.txt
playwright install chromium
```

### Bot can't find desks

1. Check your `config/booking_config.json` settings
2. Verify the desk prefix matches your SpaceIQ layout
3. Make sure you're logged in (run session warmer)

### Headless mode isn't working

1. Stop any running instances (`Ctrl+C`)
2. Run session warmer to refresh your login
3. Try visible mode first to see if there are any errors

---

## Logs and Debugging

- **Logs** are saved in `logs/` folder
- **Screenshots** are saved in `screenshots/` folder when errors occur
- Check logs if something goes wrong

---

## File Structure

```
spaceIqBotv01/
├── config/
│   ├── booking_config.json     # Your booking preferences
│   ├── locked_desks.json       # Desks to avoid
│   ├── desk_positions.json     # Position cache (auto-generated)
│   └── README.md              # Configuration documentation
├── src/                       # Bot source code
├── playwright/.auth/          # Your saved session (keep private!)
├── logs/                      # Log files
├── screenshots/               # Error screenshots
├── run.bat                    # Run bot (Windows)
├── run_headless_booking.bat   # Run headless mode (Windows)
├── run_session_warmer.bat     # Login and save session (Windows)
└── requirements.txt           # Python dependencies
```

---

## Security Notes

- **Never commit** `playwright/.auth/auth.json` to Git (contains your session)
- **Never share** your `auth.json` file with anyone
- The bot only interacts with SpaceIQ - no data is sent elsewhere
- Your credentials are never stored (only the session token)

---

## Support

For issues or questions:
1. Check the logs in `logs/` folder
2. Check `config/README.md` for configuration help
3. Check other `.md` files in the project for detailed documentation

---

## License

This project is for personal use only. Use at your own risk.
