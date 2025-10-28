# Desk Priority System - How It Works

## Your Current Preferences

The bot will try to book desks in this order:

### Priority 1 (BEST) - Range 2.24.01 to 2.24.20
**Your most preferred area**
- Desks: 2.24.01, 2.24.02, 2.24.03, ..., 2.24.20
- Bot tries these FIRST

### Priority 2 - Range 2.24.34 to 2.24.42
**Second choice**
- Desks: 2.24.34, 2.24.35, 2.24.36, ..., 2.24.42
- Bot tries these if Priority 1 not available

### Priority 3 - Range 2.24.52 to 2.24.68
**Third choice**
- Desks: 2.24.52, 2.24.53, 2.24.54, ..., 2.24.68
- Bot tries these if Priority 1-2 not available

### Priority 4 - Range 2.24.22 to 2.24.33
**Fourth choice**
- Desks: 2.24.22, 2.24.23, 2.24.24, ..., 2.24.33
- Bot tries these if Priority 1-3 not available

### Priority 5 (WORST) - Range 2.24.44 to 2.24.46
**Last resort - only if nothing else available**
- Desks: 2.24.44, 2.24.45, 2.24.46
- Bot tries these LAST

---

## How The Bot Works Now (Two-Phase Approach)

### PHASE 1: Discovery
The bot finds ALL blue circles and identifies which desk each one is:

```
[INFO] Found 10 blue circles
[INFO] PHASE 1: Identifying all blue circle desks...
[INFO] Checking circle 1/10 at (1200, 300)...
[INFO] → Identified: 2.24.05
[INFO] Checking circle 2/10 at (1250, 310)...
[INFO] → Identified: 2.24.22
[INFO] Checking circle 3/10 at (1300, 320)...
[INFO] → Identified: 2.24.35
... (continues for all circles)
[INFO] Identified 10 desks from blue circles
```

**What happens:**
- Clicks each blue dot to see which desk it is
- Closes the popup (doesn't book yet)
- Builds a map of {desk_code: coordinates}
- Continues until ALL blue dots are identified

### PHASE 2: Booking
The bot books the HIGHEST PRIORITY available desk:

```
[INFO] PHASE 2: Booking highest priority available desk...
[INFO] Available desks sorted by priority:
       Priority 1:
         - 2.24.05 (Best area - most preferred)
         - 2.24.10 (Best area - most preferred)
       Priority 2:
         - 2.24.35 (Second choice)
       Priority 4:
         - 2.24.22 (Fourth choice)

[PRIORITY] Found highest priority desk: 2.24.05 (Priority position: 1)
[INFO] Clicking to book 2.24.05 at (1200, 300)...
[SUCCESS] Successfully selected highest priority desk 2.24.05!
```

**What happens:**
- Goes through your priority list in order
- Finds the FIRST desk that has a blue circle
- Books that desk immediately
- Ignores all lower priority desks

---

## Example Scenarios

### Scenario 1: Best Area Available ✅
**Available desks:** 2.24.05, 2.24.22, 2.24.44
**Bot books:** 2.24.05 (Priority 1)
**Reason:** Your best area is available!

### Scenario 2: Only Middle Priorities Available
**Available desks:** 2.24.35, 2.24.22, 2.24.60
**Bot books:** 2.24.35 (Priority 2)
**Reason:** Priority 1 not available, so takes Priority 2

### Scenario 3: Only Worst Seats Available
**Available desks:** 2.24.44, 2.24.45
**Bot books:** 2.24.44 (Priority 5)
**Reason:** Better than no desk at all

### Scenario 4: Best and Worst Available
**Available desks:** 2.24.05, 2.24.44, 2.24.45
**Bot books:** 2.24.05 (Priority 1)
**Reason:** Always takes highest priority, ignores lower priorities

---

## Still Respects Locked Desks

The bot ALWAYS filters out locked desks from `config/locked_desks.json` BEFORE applying priorities.

**Example:**
- Priority 1 range: 2.24.01-2.24.20
- Locked desks: 2.24.01, 2.24.13, 2.24.18, 2.24.19
- Available Priority 1 desks: 2.24.02-2.24.12, 2.24.14-2.24.17, 2.24.20
- **The bot will NEVER book locked desks**, even if they're Priority 1

---

## What You'll See in Logs

```
[7/9] Finding available 2.24.* desks...
       Found 12 booking entries in sidebar
       Found 8 booked desks
       Loaded 20 locked desks from config
       Found 15 available desks: ['2.24.02', '2.24.05', '2.24.10', ...]

[INFO] Sorted desks by priority:
       Desk Priority Order (best to worst):

         Priority 1:
           - 2.24.02 (Best area - most preferred)
           - 2.24.05 (Best area - most preferred)
           - 2.24.10 (Best area - most preferred)

         Priority 2:
           - 2.24.35 (Second choice)
           - 2.24.40 (Second choice)

         Priority 3:
           - 2.24.60 (Third choice)

[8/9] Using computer vision to detect and click available desks...
       Analyzing screenshot: D:\SD\spaceIqBotv01\screenshots\floor_map_loaded_20251026_123456.png
       Found 8 blue circles
       PHASE 1: Identifying all blue circle desks...
       Checking circle 1/8 at (1200, 300)...
       → Identified: 2.24.02
       Checking circle 2/8 at (1250, 310)...
       → Identified: 2.24.05
       ... (continues)
       Identified 8 desks from blue circles
       PHASE 2: Booking highest priority available desk...
       [PRIORITY] Found highest priority desk: 2.24.02 (Priority position: 1)
       Clicking to book 2.24.02 at (1200, 300)...
       [SUCCESS] Successfully selected highest priority desk 2.24.02!

[9/9] Clicking 'Book Now'...
[SUCCESS] Booked desk 2.24.02 for 2025-11-20!
```

---

## Editing Your Priorities

To change your preferences, edit `config/booking_config.json`:

```json
{
  "desk_preferences": {
    "prefix": "2.24",
    "priority_ranges": [
      {"range": "2.24.01-2.24.20", "priority": 1, "reason": "Best area - most preferred"},
      {"range": "2.24.34-2.24.42", "priority": 2, "reason": "Second choice"},
      {"range": "2.24.52-2.24.68", "priority": 3, "reason": "Third choice"},
      {"range": "2.24.22-2.24.33", "priority": 4, "reason": "Fourth choice"},
      {"range": "2.24.44-2.24.46", "priority": 5, "reason": "Worst seats - last resort only"}
    ]
  }
}
```

**Tips:**
- Lower priority number = higher preference (1 is best)
- Ranges can overlap (first match wins)
- Desks not in any range get priority 999 (very low)
- You can add as many ranges as you want
- The "reason" field is just for your reference (not used by bot)

---

## Key Improvements Over Old Version

### OLD WAY (before this update):
❌ Bot clicked blue circles in random order (CV detection order)
❌ Booked the FIRST available desk it found
❌ No way to prefer certain areas
❌ Might book worst seats even if best seats available

### NEW WAY (current):
✅ Bot identifies ALL blue circles first
✅ Then books HIGHEST PRIORITY desk
✅ Fully respects your preferences
✅ Always gets you the best available seat

---

## Performance Impact

The two-phase approach takes slightly longer (clicks all blue dots to identify them), but:
- **Extra time:** ~5-10 seconds per booking attempt
- **Benefit:** Always books your preferred desk
- **Worth it:** You get better seats consistently

If you're in a rush and don't care about priorities, you can remove all `priority_ranges` from the config to use the old faster method.

---

## Testing

Run this to verify your priorities are configured correctly:

```bash
python test_features.py
```

You should see your priority ranges listed and tested.

---

**Your priorities are now configured and ready to use!** 🎯

The bot will ALWAYS try to book from your best area first (2.24.01-2.24.20), then work down the list.
