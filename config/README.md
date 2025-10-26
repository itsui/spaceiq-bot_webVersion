# Configuration Files

## booking_config.json

This file contains your booking preferences and the list of dates you want to book.

### How to Edit:

1. Open `booking_config.json` in any text editor
2. Add dates to the `dates_to_try` array in YYYY-MM-DD format
3. Save the file and run `python multi_date_book.py`

### Example:

```json
{
  "dates_to_try": [
    "2025-11-12",
    "2025-11-19",
    "2025-11-26"
  ],
  "desk_preferences": {
    "prefix": "2.24"
  }
}
```

### How It Works:

- Bot tries each date **once** in order
- If **no seats available** → skips to next date immediately (no waiting)
- If **seats found** → tries to book (with retries for click failures)
- **Successfully booked dates** are moved to `booked_dates` array
- **Dates with no seats** remain in `dates_to_try` for you to try again later

### Tips:

- **Add a date**: Add it to the `dates_to_try` array (e.g., `"2025-12-01"`)
- **Remove a date**: Delete the line (or let the bot remove it after successful booking)
- **Make sure to keep commas** between items (except the last one)
- **Date format**: Must be YYYY-MM-DD (e.g., "2025-11-12")

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
