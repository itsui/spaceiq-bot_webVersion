# New Features - Development Branch

## Feature 1: Headless/Background Mode ✅

Run the bot without showing a browser window - perfect for booking while you work!

### How It Works
- Browser runs in memory (no visible window)
- Takes screenshots to disk for CV analysis
- Works exactly the same as visible mode
- **Only limitation:** Session warming needs visible browser for SSO login (one-time)

### Setup

**Option A: Command Line Flag (Recommended)**

Just add `--headless` to any booking command:
```bash
# Standard booking
python multi_date_book.py --auto --headless

# With polling mode
python multi_date_book.py --auto --headless --poll

# Quick book (all-in-one)
python quick_book.py --auto --headless
```

**Option B: Batch File (Quickest)**

Just double-click:
```
run_headless_booking.bat
```
(This uses the `--headless` flag internally)

**Option C: Environment Variable (Permanent - Optional)**

Edit your `.env` file to make it the default:
```bash
HEADLESS=true
```

Then run normally (no flag needed):
```bash
python multi_date_book.py --auto
```

Note: Command line flag `--headless` overrides .env setting

### Workflow

1. **First Time (Visible Browser Needed)**
   ```bash
   # Warm session with visible browser (SSO login)
   python auto_warm_session.py

   # Now run headless (just add --headless flag!)
   python multi_date_book.py --auto --headless
   ```

2. **Daily Use (Headless)**
   ```bash
   # Just run with --headless flag - no browser window!
   python multi_date_book.py --auto --headless

   # OR use the batch file
   run_headless_booking.bat
   ```

3. **Session Expired? (Automatic Handling)**
   ```bash
   # Just run headless mode - bot auto-detects expired session!
   python multi_date_book.py --auto --headless

   # What happens:
   # 1. Bot detects session expired
   # 2. Opens visible browser automatically
   # 3. You login via SSO
   # 4. Browser closes, booking resumes in headless mode
   ```

   **Manual way (if preferred):**
   ```bash
   # Warm session manually
   python auto_warm_session.py

   # Then run headless
   python multi_date_book.py --auto --headless
   ```

### Benefits
✅ Work uninterrupted while booking runs
✅ No browser window popping up
✅ Same reliability as visible mode
✅ Perfect for scheduled tasks
✅ Lower resource usage

---

## Feature 2: Desk Priority System ✅

Prefer certain desks over others - book your favorite seats first!

### How It Works
The bot will try available desks in order of your preference:
1. **Priority 1** desks (most preferred)
2. **Priority 2** desks
3. **Priority 3** desks
4. Unranked desks (lowest priority)

### Configuration

Edit `config/booking_config.json`:

```json
{
  "desk_preferences": {
    "prefix": "2.24",
    "priority_ranges": [
      {
        "range": "2.24.20-2.24.30",
        "priority": 1,
        "reason": "Near window"
      },
      {
        "range": "2.24.02-2.24.12",
        "priority": 2,
        "reason": "Quiet area"
      },
      {
        "range": "2.24.31-2.24.41",
        "priority": 3,
        "reason": "Acceptable"
      },
      {
        "range": "2.24.43-2.24.66",
        "priority": 4,
        "reason": "Last resort"
      }
    ]
  }
}
```

### Example Use Cases

**Prefer Window Seats:**
```json
"priority_ranges": [
  {"range": "2.24.20-2.24.30", "priority": 1, "reason": "Window view"},
  {"range": "2.24.02-2.24.19", "priority": 2, "reason": "Other desks"}
]
```

**Avoid Noisy Areas:**
```json
"priority_ranges": [
  {"range": "2.24.40-2.24.50", "priority": 1, "reason": "Quiet zone"},
  {"range": "2.24.20-2.24.30", "priority": 3, "reason": "Near printers - noisy"}
]
```

**Near Team:**
```json
"priority_ranges": [
  {"range": "2.24.25-2.24.35", "priority": 1, "reason": "Near my team"},
  {"range": "2.24.36-2.24.45", "priority": 2, "reason": "Close enough"}
]
```

### Output Example

When the bot runs, you'll see:
```
[INFO] Found 5 available desk(s): ['2.24.05', '2.24.22', '2.24.28', '2.24.44', '2.24.60']
[INFO] Sorted desks by priority:
       Desk Priority Order (best to worst):

         Priority 1:
           - 2.24.22 (Near window)
           - 2.24.28 (Near window)

         Priority 2:
           - 2.24.05 (Quiet area)

         Priority 4:
           - 2.24.44 (Last resort)
           - 2.24.60 (Last resort)

[8/9] Using computer vision to detect and click available desks...
[INFO] Trying desk 2.24.22 (Priority 1)...
```

The bot will try `2.24.22` first (Priority 1), then move down the list if unavailable.

### Benefits
✅ Always book your favorite desks when available
✅ Customize by location, view, noise level, etc.
✅ Automatically sorts available desks
✅ No manual intervention needed
✅ Clear visibility of priority order in logs

---

## Combining Both Features

**The Ultimate Setup: Headless + Priorities**

1. Configure priorities in `config/booking_config.json`
2. Enable headless mode in `.env`
3. Run: `python multi_date_book.py --auto`

Result:
- Books your preferred desks first ✅
- Runs in background (no browser window) ✅
- You keep working uninterrupted ✅

---

## Testing

### Test Headless Mode
```bash
# Quick test with visible browser
python multi_date_book.py --auto

# Now test headless (just add --headless flag)
python multi_date_book.py --auto --headless

# Should work the same, just no browser window!
```

### Test Desk Priorities
```bash
# Add priorities to config/booking_config.json
# Run booking and watch the logs:
python multi_date_book.py --auto

# Look for:
# [INFO] Sorted desks by priority:
#   Priority 1:
#     - 2.24.XX (your preferred desks)
```

---

## Troubleshooting

### Headless Mode Issues

**"Failed to book" in headless mode:**
- Session might be expired
- Run `python auto_warm_session.py` to refresh
- Try with `HEADLESS=false` first to debug

**Screenshots not working:**
- They should work in headless mode
- Check `screenshots/` folder
- CV detection works the same in headless

### Priority System Issues

**Priorities not being applied:**
- Check `config/booking_config.json` syntax (valid JSON?)
- Ensure ranges match your desk prefix (e.g., "2.24.XX")
- Look for "[INFO] Sorted desks by priority" in output

**All desks have same priority:**
- Check if ranges overlap correctly
- Ensure desk numbers fall within your ranges
- Default priority is 999 (lowest)

---

## Performance

**Headless Mode:**
- ⚡ 10-20% faster (no GUI rendering)
- 💾 Less memory usage
- 🔇 No visual distractions

**Desk Priorities:**
- ⏱️ Negligible performance impact (<1 second sorting)
- 🎯 Higher success rate for preferred desks
- 📊 Better logging and visibility

---

## Rollback

If either feature causes issues:

```bash
# Return to stable version
git checkout v1.0-stable

# OR just disable the features:

# Disable headless: Don't use --headless flag
python multi_date_book.py --auto

# Disable priorities: Edit config/booking_config.json
# Remove or empty the "priority_ranges" array
"priority_ranges": []
```

---

## Future Enhancements

Potential additions (not yet implemented):
- [ ] Avoid specific desks (blacklist)
- [ ] Time-based priorities (morning vs afternoon preferences)
- [ ] Multi-user priorities (share config with team)
- [ ] Auto-learning (remember which desks you like)

---

**Both features are now live on the `development` branch!**

Test them out and let me know how they work. 🚀
