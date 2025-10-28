# Debugging Guide - Log Files

## 📁 Where to Find Logs

After every run, the bot creates **TWO log files** in the `logs/` folder:

### 1. Console Log (Everything You See)
```
logs/console_YYYYMMDD_HHMMSS.log
```
**Contains:** Exact copy of everything printed to the console
- All [INFO] messages
- All [SUCCESS] messages
- All [FAILED] messages
- Priority explanations
- Step-by-step progress

**Example:** `logs/console_20251026_235959.log`

### 2. Detailed Debug Log (Behind The Scenes)
```
logs/booking_YYYYMMDD_HHMMSS.log
```
**Contains:** Technical details for debugging
- Available desks (unsorted and sorted)
- Priority configuration
- CV detection results
- Exact desk coordinates
- Error details

**Example:** `logs/booking_20251026_235959.log`

---

## 🔍 Debugging Priority Issues

If the bot books the wrong desk (like 2.24.23 instead of 2.24.35), check these sections in the logs:

### Step 1: Check Available Desks (Console Log)

```
[7/9] Finding available 2.24.* desks...
       Found 15 available desk(s): ['2.24.05', '2.24.10', '2.24.23', '2.24.35', ...]
```

**Look for:**
- Is the higher priority desk in the list?
- Example: Is `2.24.35` in the available list?

### Step 2: Check Priority Sorting (Console Log)

```
[INFO] Sorted desks by priority:
       Desk Priority Order (best to worst):

         Priority 2:
           - 2.24.35 (Second choice)      ← Should be listed BEFORE Priority 4

         Priority 4:
           - 2.24.23 (Fourth choice)
```

**Look for:**
- Is the higher priority desk listed FIRST?
- Example: 2.24.35 (Priority 2) should appear BEFORE 2.24.23 (Priority 4)

### Step 3: Check Priority Config (Debug Log)

```
2025-10-26 23:59:59 - INFO - Priority configuration: [
  {"range": "2.24.01-2.24.20", "priority": 1, "reason": "Best area"},
  {"range": "2.24.34-2.24.42", "priority": 2, "reason": "Second choice"},
  ...
]
```

**Look for:**
- Is 2.24.35 in range 2.24.34-2.24.42? (Yes = Priority 2)
- Is 2.24.23 in range 2.24.22-2.24.33? (Yes = Priority 4)

### Step 4: Check Sorted Order (Debug Log)

```
2025-10-26 23:59:59 - INFO - Available desks (sorted by priority): ['2.24.35', '2.24.23', ...]
```

**Look for:**
- First desk in list should be highest priority
- Example: 2.24.35 should be FIRST, 2.24.23 should be SECOND

### Step 5: Check CV Detection (Console Log)

```
[8/9] Using computer vision to detect and click available desks...
       Found 10 blue circles
       PHASE 1: Identifying all blue circle desks...
       Checking circle 1/10 at (1200, 300)...
       → Identified: 2.24.23
       Checking circle 2/10 at (1250, 350)...
       → Identified: 2.24.35
       ...
       Identified 10 desks from blue circles
```

**Look for:**
- Were BOTH desks identified by CV?
- Example: Look for "→ Identified: 2.24.35" in the list

### Step 6: Check CV Detection (Debug Log)

```
2025-10-26 23:59:59 - INFO - CV Detection - Identified desks: ['2.24.23', '2.24.35', '2.24.40', ...]
```

**Look for:**
- Complete list of what CV detected
- Is the higher priority desk in this list?

### Step 7: Check Priority Matching (Console Log)

```
       PHASE 2: Booking highest priority available desk...
       [PRIORITY] Found highest priority desk: 2.24.23 (Priority position: 1/15)
       Clicking to book 2.24.23 at (1200, 300)...
       [SUCCESS] Successfully selected highest priority desk 2.24.23!
```

**Look for:**
- Which desk did it choose?
- What priority position? (1 = first in priority list)

### Step 8: Check Priority Matching (Debug Log)

```
2025-10-26 23:59:59 - INFO - PHASE 2 - Available desks (priority order): ['2.24.35', '2.24.23', ...]
2025-10-26 23:59:59 - INFO - PHASE 2 - Detected desks (from CV): ['2.24.23', '2.24.35', ...]
2025-10-26 23:59:59 - INFO - PRIORITY MATCH - Desk: 2.24.23, Priority Position: 1, Coordinates: (1200, 300)
2025-10-26 23:59:59 - INFO - This is the FIRST match in priority order - booking this desk
```

**THIS IS THE KEY!**

**If Priority Position = 1 but it's the WRONG desk:**
- The priority sorting failed
- Check: "Available desks (priority order)" - is it sorted correctly?

**If the higher priority desk is NOT in "Detected desks (from CV)":**
- CV failed to find the blue circle for that desk
- The desk was available but CV couldn't detect it

---

## 🐛 Common Issues & Solutions

### Issue 1: CV Detected Wrong Desk

**Symptoms:**
```
Available desks (sorted): ['2.24.35', '2.24.23']  ✓ Correct order
Detected desks (CV): ['2.24.23']                  ✗ 2.24.35 missing!
Priority Match: 2.24.23                           ✗ Wrong desk (only one detected)
```

**Cause:** CV failed to find blue circle for 2.24.35

**Solutions:**
- Blue circle might be obscured
- Desk might be at edge of screen
- Circle might be too small/faint
- Check screenshot: `screenshots/floor_map_loaded_*.png`

### Issue 2: Priority Sorting Failed

**Symptoms:**
```
Available desks (unsorted): ['2.24.23', '2.24.35']  ✓ Both available
Available desks (sorted): ['2.24.23', '2.24.35']    ✗ Wrong order! Should be reversed
Detected desks (CV): ['2.24.23', '2.24.35']         ✓ Both detected
Priority Match: 2.24.23                             ✗ Wrong desk (picked first in wrong order)
```

**Cause:** Priority sorting logic bug

**Solutions:**
- Check `config/booking_config.json` - are ranges correct?
- Run `python test_features.py` to verify sorting
- Check debug log for "Priority configuration"

### Issue 3: Desk Not in Available List

**Symptoms:**
```
Available desks: ['2.24.23']                        ✗ 2.24.35 missing
Reason: Desk is marked as booked or locked
```

**Cause:** Desk incorrectly filtered out

**Solutions:**
- Check if 2.24.35 is in `config/locked_desks.json` (shouldn't be)
- Check sidebar - was it already booked by someone?
- Check debug log: "Found X booked desks"

---

## 📊 Example Debug Session

**Problem:** Bot booked 2.24.23 instead of 2.24.35

**Step 1: Open Console Log**
```
logs/console_20251026_235959.log
```

**Step 2: Search for the date**
```
TRYING DATE: 2025-11-19
```

**Step 3: Check available desks**
```
[7/9] Finding available 2.24.* desks...
       Found 15 available desk(s): ['2.24.05', '2.24.23', '2.24.35', ...]
```
✓ Both desks are available

**Step 4: Check priority sorting**
```
[INFO] Sorted desks by priority:
       Priority 2:
         - 2.24.35 (Second choice)
       Priority 4:
         - 2.24.23 (Fourth choice)
```
✓ Sorting looks correct (2.24.35 listed before 2.24.23)

**Step 5: Check CV detection**
```
       PHASE 1: Identifying all blue circle desks...
       → Identified: 2.24.05
       → Identified: 2.24.23
       → Identified: 2.24.40
       (No 2.24.35!)
```
❌ **FOUND THE BUG!** CV didn't detect 2.24.35

**Root Cause:** Blue circle for 2.24.35 wasn't detected by computer vision

**Solution:**
- Check screenshot to see if blue circle is visible
- Might need to adjust CV detection threshold
- Desk is available but bot can't click it if CV can't find it

---

## 🔧 How to Share Logs for Help

1. **Find the log files:**
   ```
   logs/console_YYYYMMDD_HHMMSS.log
   logs/booking_YYYYMMDD_HHMMSS.log
   ```

2. **Find the problem section:**
   - Search for the date that had the issue
   - Copy everything from "TRYING DATE: YYYY-MM-DD" to the next date

3. **Share:**
   - Copy/paste the section
   - Or attach the full log file

---

## 📁 Log File Locations

```
spaceIqBotv01/
├── logs/
│   ├── console_20251026_235959.log  ← Everything you see in console
│   ├── booking_20251026_235959.log  ← Technical debug info
│   ├── console_20251027_120000.log
│   └── booking_20251027_120000.log
└── screenshots/
    └── floor_map_loaded_*.png       ← CV analyzes this
```

**Logs are created automatically** every time you run the bot!

---

## 🎯 Quick Checklist

When debugging a priority issue, check these in order:

1. ☐ Are both desks in "Available desks" list?
2. ☐ Is sorting correct in "Sorted desks by priority"?
3. ☐ Are both desks in "Identified desks" from CV?
4. ☐ Which desk is "FIRST match in priority order"?
5. ☐ Does Priority Position = 1 match the highest priority desk?

**If all ☐ are ✓ but wrong desk was booked → Bug in code**
**If any ☐ is ✗ → Found the issue!**

---

## 🚀 Running Test Mode

Want to see detailed logging without actually booking?

```bash
# Run test to see priority sorting
python test_features.py

# Check the output for your actual desk priorities
```

This will show you exactly how desks are being sorted without making any bookings.
