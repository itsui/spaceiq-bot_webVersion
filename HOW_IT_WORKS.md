# How The Bot Works - Complete Breakdown

## 🔄 Automatic Date Calculation

**YES - Dates are calculated fresh EVERY TIME you run the bot.**

### How It Works:

```python
# From src/workflows/multi_date_booking.py line 87-105

# ALWAYS calculate dates fresh from calendar
today = datetime.now().date()
furthest_date = today + timedelta(weeks=4, days=1)  # 29 days ahead

dates_to_try = []
current_date = today

while current_date <= furthest_date:
    # Only Wed (2) and Thu (3)
    if current_date.weekday() in [2, 3]:
        if current_date >= today:
            dates_to_try.append(current_date.strftime("%Y-%m-%d"))
    current_date += timedelta(days=1)

# Sort from furthest to closest (most available first)
dates_to_try.sort(reverse=True)
```

### What This Means:

**Example - If you run on Monday, Oct 28, 2024:**
- Calculates: Oct 28 + 29 days = Nov 26, 2024
- Finds all Wed/Thu between Oct 28 and Nov 26
- Results: Wed Oct 30, Thu Oct 31, Wed Nov 6, Thu Nov 7, etc.

**Next day - If you run on Tuesday, Oct 29, 2024:**
- Calculates: Oct 29 + 29 days = Nov 27, 2024
- Finds all Wed/Thu between Oct 29 and Nov 27
- Results: Wed Oct 30, Thu Oct 31, Wed Nov 6, Thu Nov 7, etc. (slightly different!)

**The bot NEVER remembers what it booked before** - it always calculates fresh based on TODAY + 29 days.

---

## ✅ Disabled Date Detection

**YES - The bot automatically detects and skips disabled dates.**

### How It Works:

SpaceIQ calendar uses these HTML attributes:

**Available Date:**
```html
<div class="HotelingCalendar---day"
     role="gridcell"
     aria-label="Thu Nov 20 2025"
     aria-disabled="false"     ← Can be booked
     aria-selected="false">20</div>
```

**Disabled Date (grayed out):**
```html
<div class="HotelingCalendar---day HotelingCalendar---disabled"
     role="gridcell"
     aria-label="Fri Nov 28 2025"
     aria-disabled="true"      ← Cannot be booked (beyond 29 day window)
     aria-selected="false">28</div>
```

### Bot Detection Logic:

```python
# From src/pages/spaceiq_booking_page.py line 152-165

# Look for date with aria-disabled="false"
date_cell = page.locator(
    f'div[role="gridcell"][aria-label="{aria_label}"][aria-disabled="false"]'
)

# Check if date exists but is disabled
disabled_cell = page.locator(
    f'div[role="gridcell"][aria-label="{aria_label}"][aria-disabled="true"]'
)

if await disabled_cell.count() > 0:
    print(f"[WARNING] Date {aria_label} is disabled (beyond booking window)")
    raise Exception(f"Date {aria_label} is disabled/grayed out")
```

### What Happens When Date Is Disabled:

```python
# From src/workflows/multi_date_booking.py line 297-305

try:
    await booking_page.select_date_from_calendar(days_ahead=days_ahead)
except Exception as e:
    if "disabled" in str(e).lower() or "beyond booking window" in str(e).lower():
        print(f"[SKIPPED] Date is beyond booking window (grayed out)")
        return False  # Skip to next date
    else:
        raise  # Re-raise if different error
```

**Output you'll see:**
```
[4/9] Selecting date (2025-11-28)...
       Looking for date: Fri Nov 28 2025
       [WARNING] Date Fri Nov 28 2025 is disabled (beyond booking window)
[SKIPPED] Date is beyond booking window (grayed out)
```

The bot then moves on to the next date automatically.

---

## 🎯 Complete Booking Flow

### What Happens When You Run `run_headless_booking.bat`:

```
1. Calculate Dates (Automatic)
   ├─ Today: Oct 28, 2024
   ├─ Furthest: Nov 26, 2024 (29 days)
   └─ Wed/Thu dates: Oct 30, Oct 31, Nov 6, Nov 7, etc.

2. For Each Date (Furthest First):
   ├─ Navigate to floor view
   ├─ Click "Book Desk"
   ├─ Open date picker
   ├─ Try to select date
   │  ├─ Check if aria-disabled="false" ✓
   │  └─ If aria-disabled="true" → SKIP
   ├─ Click "Update"
   ├─ Wait for floor map
   ├─ Get available desks from sidebar
   │  ├─ All desks: 2.24.01-2.24.70
   │  ├─ Minus booked desks (from sidebar)
   │  └─ Minus locked desks (from config)
   ├─ Sort by priority
   │  ├─ Priority 1: 2.24.01-2.24.20
   │  ├─ Priority 2: 2.24.34-2.24.42
   │  ├─ Priority 3: 2.24.52-2.24.68
   │  ├─ Priority 4: 2.24.22-2.24.33
   │  └─ Priority 5: 2.24.44-2.24.46
   ├─ PHASE 1: Click all blue dots to identify desks
   │  ├─ Blue dot 1 → 2.24.05 (store coordinates)
   │  ├─ Blue dot 2 → 2.24.22 (store coordinates)
   │  └─ Blue dot 3 → 2.24.35 (store coordinates)
   ├─ PHASE 2: Book highest priority desk
   │  ├─ Check available: [2.24.05, 2.24.22, 2.24.35]
   │  ├─ Check priorities: 2.24.05 = Priority 1 ✓
   │  └─ Click 2.24.05 and book it!
   └─ Verify booking success

3. Move to Next Date
   └─ Repeat until all dates tried
```

---

## 🔧 Why Dates Are Calculated Fresh Every Time

**Prevents False Positives:**

If the bot remembered "I booked Nov 20" and removed it from the list, but the booking actually failed (server error, session expired, etc.), that date would be lost forever.

**By calculating fresh every time:**
- ✅ Always tries all Wed/Thu dates within 29 days
- ✅ If a date was actually booked, sidebar will show it as booked → skipped
- ✅ If a date failed to book last time, it tries again
- ✅ If a date is beyond booking window, aria-disabled="true" → skipped

**Result:** The bot is self-healing and won't miss dates!

---

## 📊 Example Run Output

```
======================================================================
         SpaceIQ Multi-Date Booking Bot
======================================================================

Dates to book: 2025-11-20, 2025-11-19, 2025-11-13, 2025-11-12, ...
Desk prefix: 2.24.*
Max attempts per date: 10
Refresh interval: 30s
======================================================================

======================================================================
         TRYING DATE: 2025-11-20 (Furthest date - most available)
======================================================================

[1/9] Navigating to floor view...
[2/9] Clicking 'Book Desk'...
[3/9] Opening date picker...
[4/9] Selecting date (2025-11-20)...
       Looking for date: Thu Nov 20 2025
       ✓ Date is available (aria-disabled="false")
[5/9] Clicking 'Update'...
[6/9] Waiting for floor map...
[7/9] Finding available 2.24.* desks...
       Found 15 available desks
[INFO] Sorted desks by priority:
       Priority 1: 2.24.05, 2.24.10
       Priority 2: 2.24.35
       Priority 4: 2.24.22
[8/9] Using computer vision...
       PHASE 1: Identifying all blue circles...
       → Identified: 2.24.05
       → Identified: 2.24.22
       → Identified: 2.24.35
       PHASE 2: Booking highest priority...
       [PRIORITY] Found highest priority: 2.24.05
[9/9] Clicking 'Book Now'...
[SUCCESS] Booked desk 2.24.05 for 2025-11-20!

======================================================================
         TRYING DATE: 2025-11-28 (Beyond 29 day window)
======================================================================

[4/9] Selecting date (2025-11-28)...
       Looking for date: Fri Nov 28 2025
       [WARNING] Date is disabled (aria-disabled="true")
[SKIPPED] Date is beyond booking window (grayed out)

Moving to next date...
```

---

## 🚀 Run Modes

### With Confirmation (Default)
```bash
python multi_date_book.py --auto
```
Output: `Press Enter to start booking (or Ctrl+C to cancel)...`

### Fully Automatic (No Prompts)
```bash
python multi_date_book.py --auto --unattended
```
Output: `[UNATTENDED MODE] Starting booking automatically...`

### Headless + Automatic (Recommended)
```bash
python multi_date_book.py --auto --headless --unattended
```
OR just double-click: `run_headless_booking.bat`

---

## 📅 Daily Usage Pattern

**Monday (No Action Needed)**
- 29-day window: Mon Oct 28 → Tue Nov 26
- Available Wed/Thu: Oct 30, Oct 31, Nov 6, 7, 13, 14, 20, 21

**Tuesday 11:59 PM (Run Bot)**
```bash
run_headless_booking.bat
```
- 29-day window: Tue Oct 29 → Wed Nov 27
- Available Wed/Thu: Oct 30, Oct 31, Nov 6, 7, 13, 14, 20, 21, **Nov 27** (NEW!)
- Bot tries to book **Nov 27** (newest date in window)

**Wednesday 11:59 PM (Run Bot Again)**
```bash
run_headless_booking.bat
```
- 29-day window: Wed Oct 30 → Thu Nov 28
- Available Wed/Thu: Oct 31, Nov 6, 7, 13, 14, 20, 21, 27, **Nov 28** (NEW!)
- Bot tries to book **Nov 28** (newest date in window)

**Every day, new dates become available as the window moves forward!**

---

## ✅ Summary

### Your Questions Answered:

**Q: "Is the script calculating the next few days automatically?"**
**A:** YES - Every time you run it, it calculates TODAY + 29 days and finds all Wed/Thu dates in that window.

**Q: "How does it know which dates are disabled?"**
**A:** It checks `aria-disabled` attribute:
- `aria-disabled="false"` → Available, tries to book
- `aria-disabled="true"` → Disabled, skips automatically

**Q: "Does it ask for confirmation?"**
**A:** Only if you don't use `--unattended` flag. The batch file now uses it, so **no confirmation needed!**

---

**Just run:**
```
run_headless_booking.bat
```

And it handles everything automatically! 🎉
