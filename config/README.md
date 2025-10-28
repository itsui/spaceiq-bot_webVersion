# Configuration Files

## booking_config.json

This file contains your booking preferences and the list of dates you want to book.

### How to Edit:

1. Open `booking_config.json` in any text editor
2. Modify any settings you want to change
3. Save the file and run the bot

---

## Settings Reference

### 1. Building & Floor
```json
"building": "LC",
"floor": "2"
```
Set your building code and floor number.

---

### 2. Booking Days (Which Weekdays to Book)
```json
"booking_days": {
  "weekdays": [2, 3]
}
```

**Weekday Numbers:**
- `0` = Monday
- `1` = Tuesday
- `2` = Wednesday
- `3` = Thursday
- `4` = Friday
- `5` = Saturday
- `6` = Sunday

**Examples:**
- `[2, 3]` = Wednesday and Thursday only (default)
- `[0, 1, 2, 3, 4]` = All weekdays (Mon-Fri)
- `[1, 3]` = Tuesday and Thursday only
- `[2]` = Wednesday only

---

### 3. Wait Times Between Rounds
```json
"wait_times": {
  "rounds_1_to_5": {
    "seconds": 60
  },
  "rounds_6_to_15": {
    "seconds": 300
  },
  "rounds_16_plus": {
    "seconds": 900
  }
}
```

**How it works:**
The bot uses **progressive backoff** - checking aggressively at first, then slowing down:
- **Rounds 1-5**: Check every 60 seconds (1 minute)
- **Rounds 6-15**: Check every 300 seconds (5 minutes)
- **Rounds 16+**: Check every 900 seconds (15 minutes)

**Why progressive backoff?**
Early rounds are most likely to find cancellations, so we check frequently. Later rounds check less often to avoid unnecessary requests.

**To customize:** Change the `seconds` values:
- `60` = 1 minute
- `120` = 2 minutes
- `300` = 5 minutes
- `600` = 10 minutes
- `900` = 15 minutes

---

### 4. Desk Preferences
```json
"desk_preferences": {
  "prefix": "2.24",
  "priority_ranges": [
    {
      "range": "2.24.01-2.24.20",
      "priority": 1,
      "reason": "Best area"
    }
  ]
}
```

**How it works:**
- `prefix`: Only book desks starting with this prefix (e.g., "2.24")
- `priority_ranges`: Preferred desk ranges in order of preference
  - Priority 1 = Most preferred
  - Priority 2 = Second choice
  - etc.

The bot will try to book the highest priority desk available.

---

### 5. Dates

#### dates_to_try
```json
"dates_to_try": [
  "2025-11-12",
  "2025-11-19"
]
```
Manual list of dates you want to book.

**Note:** In continuous loop mode, the bot automatically generates dates based on your `booking_days` settings, so you typically don't need to manually add dates here.

#### booked_dates
```json
"booked_dates": [
  "2025-10-30",
  "2025-10-31"
]
```
**Automatically maintained** by the bot. Successfully booked dates are moved here.

---

## How It Works

### One-Time Mode (polling_book.py):
- Bot tries each date in `dates_to_try` **once** in order
- If **no seats available** → skips to next date immediately (no waiting)
- If **seats found** → tries to book (with retries for click failures)
- **Successfully booked dates** are moved to `booked_dates`

### Continuous Loop Mode (headless mode):
- Bot generates dates automatically based on `booking_days` settings
- Checks for available seats on all configured weekdays
- Uses progressive wait times between rounds
- Keeps running indefinitely until stopped

---

## Tips

- **Date format**: Must be YYYY-MM-DD (e.g., "2025-11-12")
- **Commas**: Keep commas between items (except the last one)
- **Testing changes**: After editing, save the file and restart the bot
- **Weekdays**: Use numbers 0-6 (Monday=0, Sunday=6)
- **Wait times**: Use seconds (60=1min, 300=5min, 900=15min)

---

## locked_desks.json

This file contains the list of permanently locked/unavailable desks that cannot be booked.

### How to Edit:

1. Open `locked_desks.json` in any text editor
2. Find the desk prefix you want to modify (e.g., "2.24")
3. Add or remove desk codes from the array

### Example:

```json
{
  "locked_desks": {
    "2.24": [
      "2.24.01",
      "2.24.13",
      "2.24.20"
    ]
  }
}
```

### Tips:

- **Add a locked desk**: Add the desk code to the array (e.g., `"2.24.99"`)
- **Remove a locked desk**: Delete the line with that desk code
- **Make sure to keep commas** between items (except the last one)
- **Save the file** and restart the bot

### Format:

- Use desk codes exactly as they appear in SpaceIQ (e.g., "2.24.28")
- Each desk code should be in quotes
- Separate desk codes with commas
- No comma after the last item in the array
